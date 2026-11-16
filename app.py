import sys
import asyncio
import os
import uuid
import shutil
import zipfile
import subprocess
from typing import List, Dict, Any, Optional

if sys.platform == "win32":
    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport
        orig_call_connection_lost = _ProactorBasePipeTransport._call_connection_lost

        def patched_call_connection_lost(self, exc):
            try:
                orig_call_connection_lost(self, exc)
            except (ConnectionResetError, OSError):
                pass

        _ProactorBasePipeTransport._call_connection_lost = patched_call_connection_lost
    except Exception:
        pass
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import json

import transformer

app = FastAPI(title="Unicode Assignment Transformer & PDF Studio")

# Working storage directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
UPLOADS_DIR = os.path.join(STORAGE_DIR, "uploads")
OUTPUTS_DIR = os.path.join(STORAGE_DIR, "outputs")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# In-memory registry of uploaded and processed files
# file_id -> { "name": ..., "orig_path": ..., "docx_out": ..., "pdf_out": ..., "stats": ... }
FILE_REGISTRY: Dict[str, Dict[str, Any]] = {}

class RuleItem(BaseModel):
    find: str
    replace: str
    unicode: Optional[str] = ""
    name: Optional[str] = ""
    enabled: bool = True

class ProcessRequest(BaseModel):
    file_id: str
    rules: List[RuleItem]
    cover_mode: str = "remove_cover"  # "remove_cover", "keep_untouched", "entire_doc"
    skip_urls: bool = True
    skip_headings: bool = False
    remove_page_numbers: bool = True
    custom_marker: Optional[str] = None

class BatchProcessRequest(BaseModel):
    file_ids: List[str]
    rules: List[RuleItem]
    cover_mode: str = "remove_cover"
    skip_urls: bool = True
    skip_headings: bool = False
    remove_page_numbers: bool = True
    custom_marker: Optional[str] = None
    include_docx: bool = True

@app.get("/", response_class=HTMLResponse)
@app.get("/app-view", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Unicode Studio Loading...</h1>")

@app.get("/api/rules/defaults")
async def get_default_rules():
    return {
        "default_rules": transformer.DEFAULT_RULES,
        "extended_rules": transformer.EXTENDED_RULES
    }

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload one or multiple .docx files (up to 100+ files at once)."""
    results = []
    for f in files:
        if not f.filename.lower().endswith(".docx"):
            continue
        file_id = str(uuid.uuid4())[:8]
        safe_name = os.path.basename(f.filename)
        save_path = os.path.join(UPLOADS_DIR, f"{file_id}_{safe_name}")
        
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)
            
        file_size = os.path.getsize(save_path)
        FILE_REGISTRY[file_id] = {
            "file_id": file_id,
            "name": safe_name,
            "orig_path": save_path,
            "size": file_size,
            "status": "uploaded"
        }
        results.append({
            "file_id": file_id,
            "name": safe_name,
            "size": file_size
        })
    return {"uploaded": results, "count": len(results)}

@app.post("/api/load-sample")
async def load_sample_file():
    """Loads the pre-packaged assignment sample for instant demonstration."""
    sample_src = os.path.join(BASE_DIR, "sample_assignment_extracted.docx")
    if not os.path.exists(sample_src):
        raise HTTPException(status_code=404, detail="Sample file not found on disk")
        
    file_id = str(uuid.uuid4())[:8]
    safe_name = "Unit 1 Health & Social Care Assignment.docx"
    save_path = os.path.join(UPLOADS_DIR, f"{file_id}_{safe_name}")
    shutil.copy(sample_src, save_path)
    
    file_size = os.path.getsize(save_path)
    FILE_REGISTRY[file_id] = {
        "file_id": file_id,
        "name": safe_name,
        "orig_path": save_path,
        "size": file_size,
        "status": "uploaded"
    }
    return {
        "file_id": file_id,
        "name": safe_name,
        "size": file_size
    }

@app.post("/api/preview")
async def preview_document(req: ProcessRequest):
    """Generates preview data (highlighted text, stats, and real page renders)."""
    if req.file_id not in FILE_REGISTRY:
        raise HTTPException(status_code=404, detail="File ID not found in registry")
        
    file_item = FILE_REGISTRY[req.file_id]
    rules_dicts = [r.dict() for r in req.rules]
    
    try:
        preview_data = transformer.generate_preview_data(
            docx_path=file_item["orig_path"],
            rules=rules_dicts,
            cover_mode=req.cover_mode,
            skip_urls=req.skip_urls,
            skip_headings=req.skip_headings,
            remove_page_numbers=req.remove_page_numbers,
            custom_marker=req.custom_marker,
            max_pages=4
        )
        return {
            "status": "success",
            "file_id": req.file_id,
            "file_name": file_item["name"],
            "preview": preview_data
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process-single")
async def process_single(req: ProcessRequest):
    """Processes a single file and converts it to both .docx and authentic selectable PDF."""
    if req.file_id not in FILE_REGISTRY:
        raise HTTPException(status_code=404, detail="File ID not found")
        
    file_item = FILE_REGISTRY[req.file_id]
    rules_dicts = [r.dict() for r in req.rules]
    
    out_base = os.path.splitext(file_item["name"])[0] + "_UnicodeTransformed"
    out_docx = os.path.join(OUTPUTS_DIR, f"{req.file_id}_{out_base}.docx")
    out_pdf = os.path.join(OUTPUTS_DIR, f"{req.file_id}_{out_base}.pdf")
    
    try:
        stats = transformer.transform_docx(
            input_path=file_item["orig_path"],
            output_path=out_docx,
            rules=rules_dicts,
            cover_mode=req.cover_mode,
            skip_urls=req.skip_urls,
            skip_headings=req.skip_headings,
            remove_page_numbers=req.remove_page_numbers,
            custom_marker=req.custom_marker
        )
        
        pdf_ok = transformer.convert_docx_to_pdf(out_docx, out_pdf)
        
        file_item["docx_out"] = out_docx
        file_item["pdf_out"] = out_pdf if (pdf_ok and os.path.exists(out_pdf)) else None
        file_item["stats"] = stats
        file_item["status"] = "processed"
        
        return {
            "status": "success",
            "file_id": req.file_id,
            "pdf_available": file_item["pdf_out"] is not None,
            "stats": stats
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/batch-process")
async def batch_process(req: BatchProcessRequest):
    """
    Processes all queued files (1 to 100+ files) in a batch:
    - Applies Unicode replacements with exact formatting preservation
    - Generates vector selectable-text PDFs
    - Bundles all converted files into a downloadable .ZIP file
    """
    if not req.file_ids:
        raise HTTPException(status_code=400, detail="No files provided for batch processing")
        
    rules_dicts = [r.dict() for r in req.rules]
    batch_id = str(uuid.uuid4())[:8]
    batch_zip_path = os.path.join(OUTPUTS_DIR, f"Batch_Unicode_Assignments_{batch_id}.zip")
    
    processed_items = []
    total_files = len(req.file_ids)
    overall_replacements = 0
    
    # Process DOCX transformations first
    docx_to_convert = []
    
    for f_id in req.file_ids:
        if f_id not in FILE_REGISTRY:
            continue
        item = FILE_REGISTRY[f_id]
        out_base = os.path.splitext(item["name"])[0] + "_Unicode"
        out_docx = os.path.join(OUTPUTS_DIR, f"{f_id}_{out_base}.docx")
        out_pdf = os.path.join(OUTPUTS_DIR, f"{f_id}_{out_base}.pdf")
        
        try:
            stats = transformer.transform_docx(
                input_path=item["orig_path"],
                output_path=out_docx,
                rules=rules_dicts,
                cover_mode=req.cover_mode,
                skip_urls=req.skip_urls,
                skip_headings=req.skip_headings,
                remove_page_numbers=req.remove_page_numbers,
                custom_marker=req.custom_marker
            )
            overall_replacements += stats.get("total_replacements", 0)
            item["docx_out"] = out_docx
            item["pdf_out"] = out_pdf
            item["stats"] = stats
            docx_to_convert.append((out_docx, out_pdf, item["name"]))
            processed_items.append({
                "file_id": f_id,
                "name": item["name"],
                "status": "docx_ready",
                "stats": stats
            })
        except Exception as e:
            print(f"Error transforming {item['name']}: {e}")
            processed_items.append({
                "file_id": f_id,
                "name": item["name"],
                "status": "error",
                "error": str(e)
            })

    # Batch convert all docx to pdf using LibreOffice CLI in multi-file mode
    soffice = transformer.find_libreoffice()
    if soffice and docx_to_convert:
        try:
            cmd = [soffice, "--headless", "--convert-to", "pdf"] + [d[0] for d in docx_to_convert] + ["--outdir", OUTPUTS_DIR]
            subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        except Exception as e:
            print(f"Batch LibreOffice conversion error: {e}")
            
    # For any that failed or if LibreOffice not available, try individual fallback
    for out_docx, out_pdf, _ in docx_to_convert:
        if not os.path.exists(out_pdf):
            transformer.convert_docx_to_pdf(out_docx, out_pdf)

    # Bundle all processed files into single .ZIP
    with zipfile.ZipFile(batch_zip_path, "w", zipfile.ZIP_DEFLATED) as zip_f:
        for out_docx, out_pdf, orig_name in docx_to_convert:
            clean_base = os.path.splitext(orig_name)[0]
            # Add PDF
            if os.path.exists(out_pdf):
                zip_f.write(out_pdf, arcname=f"PDFs/{clean_base}_Unicode.pdf")
            # Optionally add DOCX
            if req.include_docx and os.path.exists(out_docx):
                zip_f.write(out_docx, arcname=f"DOCX/{clean_base}_Unicode.docx")
                
    return {
        "status": "success",
        "batch_id": batch_id,
        "total_files": total_files,
        "processed_count": len(docx_to_convert),
        "overall_replacements": overall_replacements,
        "download_url": f"/api/download-batch/{batch_id}",
        "processed_items": processed_items
    }

@app.get("/api/download-batch/{batch_id}")
async def download_batch_zip(batch_id: str):
    """Download the batch-generated .ZIP archive."""
    zip_path = os.path.join(OUTPUTS_DIR, f"Batch_Unicode_Assignments_{batch_id}.zip")
    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Batch zip not found")
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"Batch_Unicode_Assignments_{batch_id}.zip"
    )

@app.get("/api/download-file/{file_id}/{ftype}")
async def download_file(file_id: str, ftype: str):
    """Download individual transformed PDF or DOCX."""
    if file_id not in FILE_REGISTRY:
        raise HTTPException(status_code=404, detail="File ID not found")
        
    item = FILE_REGISTRY[file_id]
    if ftype.lower() == "pdf":
        path = item.get("pdf_out")
        if not path or not os.path.exists(path):
            # Try to build it if docx_out exists
            if item.get("docx_out") and os.path.exists(item["docx_out"]):
                pdf_target = os.path.splitext(item["docx_out"])[0] + ".pdf"
                if transformer.convert_docx_to_pdf(item["docx_out"], pdf_target):
                    path = pdf_target
                    item["pdf_out"] = path
        if not path or not os.path.exists(path):
            raise HTTPException(status_code=404, detail="PDF has not been generated yet")
        filename = os.path.splitext(item["name"])[0] + "_Unicode.pdf"
        return FileResponse(path, media_type="application/pdf", filename=filename)
        
    elif ftype.lower() == "docx":
        path = item.get("docx_out")
        if not path or not os.path.exists(path):
            raise HTTPException(status_code=404, detail="DOCX has not been generated yet")
        filename = os.path.splitext(item["name"])[0] + "_Unicode.docx"
        return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=filename)
    else:
        raise HTTPException(status_code=400, detail="Invalid file type")

# ZeroGPU compatibility for Hugging Face Spaces
try:
    import spaces
    @spaces.GPU
    def dummy_gpu_init():
        return True
except Exception:
    pass

# Gradio compatibility wrapper for Hugging Face Spaces deployment
try:
    import gradio as gr
    with gr.Blocks(title="Assignment Unicode Transformer & PDF Studio") as demo:
        gr.HTML('<iframe src="/app-view" style="position:fixed; top:0; left:0; width:100%; height:100%; border:none; z-index:99999;"></iframe>')
    demo.app.mount("/app-view", app)
    demo.app.mount("/api", app)
    demo.app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    demo.app.router.routes = app.router.routes + demo.app.router.routes
except Exception:
    demo = None

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    if demo is not None:
        demo.launch(server_name="0.0.0.0", server_port=port)
    else:
        uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
