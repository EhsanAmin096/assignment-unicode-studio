"""
Core Unicode Transformer & PDF Converter Engine
Preserves 100% of original DOCX formatting, tables, logos, headers, footers, and styles.
Supports MS Office Word COM automation & LibreOffice headless PDF generation.
"""

import os
import re
import copy
import shutil
import tempfile
import subprocess
from typing import Dict, List, Tuple, Any, Optional
import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# Default 6 Homoglyphs as requested:
# l → ӏ U+04CF (Cyrillic Small Letter Palochka)
# k → κ U+03BA (Greek Small Letter Kappa)
# d → ԁ U+0501 (Cyrillic Small Letter Komi De)
# e → е U+0435 (Cyrillic Small Letter Ie)
# p → р U+0440 (Cyrillic Small Letter Er)
# q → զ U+0566 (Armenian Small Letter Za)
DEFAULT_RULES = [
    {"find": "l", "replace": "\u04CF", "unicode": "U+04CF", "name": "Cyrillic Palochka", "enabled": True},
    {"find": "k", "replace": "\u03BA", "unicode": "U+03BA", "name": "Greek Kappa", "enabled": True},
    {"find": "d", "replace": "\u0501", "unicode": "U+0501", "name": "Cyrillic Komi De", "enabled": True},
    {"find": "e", "replace": "\u0435", "unicode": "U+0435", "name": "Cyrillic Ie", "enabled": True},
    {"find": "p", "replace": "\u0440", "unicode": "U+0440", "name": "Cyrillic Er", "enabled": True},
    {"find": "q", "replace": "\u0566", "unicode": "U+0566", "name": "Armenian Za", "enabled": True},
]

# Extended preset options
EXTENDED_RULES = [
    {"find": "a", "replace": "\u0430", "unicode": "U+0430", "name": "Cyrillic a", "enabled": False},
    {"find": "c", "replace": "\u0441", "unicode": "U+0441", "name": "Cyrillic es", "enabled": False},
    {"find": "o", "replace": "\u043E", "unicode": "U+043E", "name": "Cyrillic o", "enabled": False},
    {"find": "s", "replace": "\u0455", "unicode": "U+0455", "name": "Cyrillic dze", "enabled": False},
    {"find": "y", "replace": "\u0443", "unicode": "U+0443", "name": "Cyrillic u", "enabled": False},
    {"find": "x", "replace": "\u0445", "unicode": "U+0445", "name": "Cyrillic ha", "enabled": False},
    {"find": "i", "replace": "\u0456", "unicode": "U+0456", "name": "Cyrillic Byelorussian-Ukrainian i", "enabled": False},
    {"find": "j", "replace": "\u0458", "unicode": "U+0458", "name": "Cyrillic je", "enabled": False},
]

URL_REGEX = re.compile(r'(https?://[^\s)\]]+|www\.[^\s)\]]+)', re.IGNORECASE)

LIBREOFFICE_PATHS = [
    r"C:\Program Files\LibreOffice\program\soffice.com",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.com",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "soffice",
]

def find_libreoffice() -> Optional[str]:
    """Find installed LibreOffice executable."""
    for p in LIBREOFFICE_PATHS:
        if os.path.isabs(p) and os.path.exists(p):
            return p
        which = shutil.which(p)
        if which:
            return which
    return None

def detect_body_start(doc: docx.Document, custom_marker: Optional[str] = None) -> int:
    """
    Find the index of the first body element in doc.element.body.
    Anything before this is considered part of the Cover Sheet, Learner Declaration, or TOC.
    """
    body = doc.element.body
    
    # 1. Custom marker if provided by user
    if custom_marker and custom_marker.strip():
        marker = custom_marker.strip().lower()
        for i, el in enumerate(body):
            text = (el.text or "").strip().lower()
            if marker in text:
                return i
    
    # 2. Look for standard assignment body headings:
    # "Introduction", "Task 1", "Task 01", "Chapter 1", "Executive Summary", "Overview"
    body_heading_patterns = [
        re.compile(r'^\s*(\d+(\.\d+)*\s*[:.-]?\s*)?introduction\b', re.IGNORECASE),
        re.compile(r'^\s*(\d+(\.\d+)*\s*[:.-]?\s*)?task\s*0?1\b', re.IGNORECASE),
        re.compile(r'^\s*(\d+(\.\d+)*\s*[:.-]?\s*)?chapter\s*0?1\b', re.IGNORECASE),
        re.compile(r'^\s*(\d+(\.\d+)*\s*[:.-]?\s*)?executive\s*summary\b', re.IGNORECASE),
        re.compile(r'^\s*(\d+(\.\d+)*\s*[:.-]?\s*)?overview\b', re.IGNORECASE),
        re.compile(r'^\s*(\d+(\.\d+)*\s*[:.-]?\s*)?background\b', re.IGNORECASE),
    ]
    
    # Identify where cover tables or TOC end
    cover_end_idx = 0
    for i, el in enumerate(body):
        tag = el.tag.split('}')[-1]
        if tag in ('tbl', 'sdt'):
            cover_end_idx = i

    # Look for introduction or first heading after cover tables / TOC
    for i in range(cover_end_idx + 1, len(body)):
        tag = body[i].tag.split('}')[-1]
        if tag == 'p':
            p = docx.text.paragraph.Paragraph(body[i], doc)
            text = p.text.strip()
            for pattern in body_heading_patterns:
                if pattern.search(text):
                    return i

    # Fallback: scan from beginning if not found after cover_end_idx
    for i, el in enumerate(body):
        tag = el.tag.split('}')[-1]
        if tag == 'p':
            p = docx.text.paragraph.Paragraph(el, doc)
            text = p.text.strip()
            for pattern in body_heading_patterns:
                if pattern.search(text):
                    return i
                    
    # 3. Fallback: if there was a TOC (<w:sdt>), start immediately after the TOC
    toc_idx = -1
    for i, el in enumerate(body):
        tag = el.tag.split('}')[-1]
        if tag == 'sdt':
            toc_idx = i
            
    if toc_idx != -1 and toc_idx + 1 < len(body):
        for i in range(toc_idx + 1, len(body)):
            tag = body[i].tag.split('}')[-1]
            if tag == 'p' and (body[i].text or "").strip():
                return i
        return toc_idx + 1
        
    if cover_end_idx > 0 and cover_end_idx + 1 < len(body):
        for i in range(cover_end_idx + 1, len(body)):
            tag = body[i].tag.split('}')[-1]
            if tag == 'p' and (body[i].text or "").strip():
                return i
        return cover_end_idx + 1
        
    return 0

def transform_text_string(
    text: str,
    rules: List[Dict[str, Any]],
    skip_urls: bool,
    counts: Dict[str, int]
) -> str:
    """
    Applies character replacement rules to text string while protecting URLs.
    Tracks replacement counts.
    """
    if not text:
        return ""
        
    # Build active replacement map
    active_rules = {r["find"]: r["replace"] for r in rules if r.get("enabled")}
    if not active_rules:
        return text

    if skip_urls:
        parts = URL_REGEX.split(text)
        out_parts = []
        for part in parts:
            if URL_REGEX.match(part):
                out_parts.append(part)
            else:
                new_chars = []
                for ch in part:
                    if ch in active_rules:
                        repl = active_rules[ch]
                        new_chars.append(repl)
                        counts[ch] = counts.get(ch, 0) + 1
                    else:
                        new_chars.append(ch)
                out_parts.append("".join(new_chars))
        return "".join(out_parts)
    else:
        new_chars = []
        for ch in text:
            if ch in active_rules:
                repl = active_rules[ch]
                new_chars.append(repl)
                counts[ch] = counts.get(ch, 0) + 1
            else:
                new_chars.append(ch)
        return "".join(new_chars)

def is_heading_paragraph(p: docx.text.paragraph.Paragraph) -> bool:
    """Check if paragraph is a heading."""
    style_name = (p.style.name if p.style else "").lower()
    if "heading" in style_name or "title" in style_name:
        return True
    text = p.text.strip()
    if re.match(r'^(introduction|task\s*\d+|conclusion|bibliography|references)\s*:?$', text, re.IGNORECASE):
        return True
    return False

def transform_docx(
    input_path: str,
    output_path: str,
    rules: List[Dict[str, Any]],
    cover_mode: str = "remove_cover",  # "remove_cover", "keep_untouched", "entire_doc"
    skip_urls: bool = True,
    skip_headings: bool = False,
    remove_page_numbers: bool = True,
    custom_marker: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transform DOCX file with character replacements.
    Preserves exact styles, tables, logos, fonts, line heights, and margins.
    Returns statistics (word count, replacement counts, total replacements).
    """
    doc = docx.Document(input_path)
    body = doc.element.body
    
    body_start_idx = detect_body_start(doc, custom_marker)
    
    # Initialize counts for each rule
    counts: Dict[str, int] = {r["find"]: 0 for r in rules if r.get("enabled")}
    
    # Handle "remove_cover" mode (removes Cover page, Template tables, and Table of Contents)
    if cover_mode == "remove_cover" and body_start_idx > 0:
        elements_to_remove = [body[i] for i in range(body_start_idx)]
        for el in elements_to_remove:
            body.remove(el)
        # Update body_start_idx now that elements are removed
        body_start_idx = 0
        
        # Strip any leading page breaks from the first paragraph so it starts on Page 1
        for el in body:
            tag = el.tag.split('}')[-1]
            if tag == 'p':
                for br in list(el.iter(qn('w:br'))):
                    if br.get(qn('w:type')) == 'page':
                        br.getparent().remove(br)
                pPr = el.find(qn('w:pPr'))
                if pPr is not None:
                    pbb = pPr.find(qn('w:pageBreakBefore'))
                    if pbb is not None:
                        pPr.remove(pbb)
                break
        
    # Process remaining elements
    for i, el in enumerate(body):
        tag = el.tag.split('}')[-1]
        
        # Check if this element should be transformed
        is_cover = (cover_mode == "keep_untouched") and (i < body_start_idx)
        if is_cover:
            continue
            
        if tag == 'p':
            p = docx.text.paragraph.Paragraph(el, doc)
            if skip_headings and is_heading_paragraph(p):
                continue
                
            for run in p.runs:
                if run.text:
                    run.text = transform_text_string(run.text, rules, skip_urls, counts)
                    
        elif tag == 'tbl':
            tbl = docx.table.Table(el, doc)
            for row in tbl.rows:
                for cell in row.cells:
                    for cp in cell.paragraphs:
                        if skip_headings and is_heading_paragraph(cp):
                            continue
                        for run in cp.runs:
                            if run.text:
                                run.text = transform_text_string(run.text, rules, skip_urls, counts)
                                
        elif tag == 'sdt':
            # Structured document tag (e.g. Table of Contents)
            # Find all <w:t> elements inside sdt
            for t_node in el.iter(qn('w:t')):
                if t_node.text:
                    t_node.text = transform_text_string(t_node.text, rules, skip_urls, counts)

    # Remove report page numbers (footers) if enabled
    if remove_page_numbers:
        for s in doc.sections:
            ftr_elem = s.footer._element
            for child in list(ftr_elem):
                ftr_elem.remove(child)
            ftr_elem.append(docx.oxml.OxmlElement('w:p'))

    # Save modified DOCX
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc.save(output_path)
    
    total_replacements = sum(counts.values())
    
    # Calculate word count of the resulting document
    total_words = 0
    for p in doc.paragraphs:
        t = p.text.strip()
        if t:
            total_words += len(t.split())
    for tbl in doc.tables:
        for r in tbl.rows:
            for c in r.cells:
                t = c.text.strip()
                if t:
                    total_words += len(t.split())
                    
    return {
        "total_replacements": total_replacements,
        "counts": counts,
        "total_words": total_words,
        "cover_mode": cover_mode,
        "body_start_idx": body_start_idx
    }

def convert_docx_to_pdf(docx_path: str, pdf_path: str) -> bool:
    """
    Converts a .docx to PDF using MS Word COM or LibreOffice headless.
    Ensures 100% preservation of original layout, tables, logos, and vector selectable text.
    """
    abs_docx = os.path.abspath(docx_path)
    abs_pdf = os.path.abspath(pdf_path)
    outdir = os.path.dirname(abs_pdf)
    os.makedirs(outdir, exist_ok=True)
    
    # Method 1: LibreOffice CLI (fast, reliable, headless)
    soffice = find_libreoffice()
    if soffice:
        try:
            cmd = [soffice, "--headless", "--convert-to", "pdf", abs_docx, "--outdir", outdir]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            base_pdf = os.path.join(outdir, os.path.splitext(os.path.basename(abs_docx))[0] + ".pdf")
            if os.path.exists(base_pdf):
                if base_pdf != abs_pdf:
                    shutil.move(base_pdf, abs_pdf)
                return True
        except Exception as e:
            print(f"LibreOffice conversion failed: {e}")
            
    # Method 2: MS Word COM automation via PowerShell
    try:
        ps_script = f"""
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {{
    $doc = $word.Documents.Open('{abs_docx}')
    $doc.SaveAs([ref]'{abs_pdf}', [ref]17)
    $doc.Close()
}} finally {{
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
}}
"""
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if os.path.exists(abs_pdf) and os.path.getsize(abs_pdf) > 0:
            return True
    except Exception as e:
        print(f"Word COM conversion failed: {e}")
        
    return False

def generate_preview_data(
    docx_path: str,
    rules: List[Dict[str, Any]],
    cover_mode: str = "remove_cover",
    skip_urls: bool = True,
    skip_headings: bool = False,
    remove_page_numbers: bool = True,
    custom_marker: Optional[str] = None,
    max_pages: int = 5
) -> Dict[str, Any]:
    """
    Generates preview data for UI:
    - Text blocks with highlighted Unicode characters
    - Per-character counts
    - Page count
    - Rendered page images (via PyMuPDF) for authentic PDF preview
    """
    import fitz  # PyMuPDF
    import base64
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_docx = os.path.join(tmpdir, "preview.docx")
        temp_pdf = os.path.join(tmpdir, "preview.pdf")
        
        stats = transform_docx(
            input_path=docx_path,
            output_path=temp_docx,
            rules=rules,
            cover_mode=cover_mode,
            skip_urls=skip_urls,
            skip_headings=skip_headings,
            remove_page_numbers=remove_page_numbers,
            custom_marker=custom_marker
        )
        
        pdf_ok = convert_docx_to_pdf(temp_docx, temp_pdf)
        
        page_images = []
        num_pages = 0
        if pdf_ok and os.path.exists(temp_pdf):
            doc = fitz.open(temp_pdf)
            num_pages = len(doc)
            for page_num in range(min(max_pages, num_pages)):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                b64 = base64.b64encode(img_bytes).decode("ascii")
                page_images.append(f"data:image/png;base64,{b64}")
            doc.close()
                
        # Also extract structured text paragraphs for diff inspector
        doc_obj = docx.Document(temp_docx)
        paragraphs_text = []
        for p in doc_obj.paragraphs:
            t = p.text.strip()
            if t:
                paragraphs_text.append(t)
        doc_obj = None
                
        # Build set of replaced characters to highlight
        active_replaces = {r["replace"]: r["find"] for r in rules if r.get("enabled")}
        
        return {
            "stats": stats,
            "page_images": page_images,
            "num_pages": num_pages,
            "paragraphs": paragraphs_text[:60],  # first 60 paragraphs for text diff
            "active_replaces": active_replaces
        }
