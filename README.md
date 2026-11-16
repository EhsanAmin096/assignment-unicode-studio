---
title: Assignment Unicode Studio
emoji: 📄
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: 6.32.0
app_file: app.py
pinned: false
---

# Unicode Assignment Transformer & PDF Studio

Ek mukammal Web App tool jo English `.docx` assignments par selective Unicode Homoglyph character replacements apply karta hai aur **100% original formatting, college logos, cover sheet tables, headers, footers, aur bibliography URLs ko bilkul kharab kiye baghair** authentic selectable-text PDF aur .docx files mein convert karta hai.

---

## 🚀 Tool Chalane Ka Tareeqa (Quick Start)

### 1. Local PC par Chalana:
- Folder mein **`run_app.bat`** file par double click karein.
- Browser **`http://127.0.0.1:8000`** par open ho jayega.

### 2. Same Wi-Fi / Local Network (Mobile / Tablet / Other PC):
- Apne mobile ya kisi doosre computer ke browser mein yeh link open karein:
  **`http://192.168.1.43:8000`**

### 3. Public Open Internet Link (Duniya mein kahin se bhi access karne ke liye):
- Folder mein **`run_public_tunnel.bat`** par double click karein. Yeh aapko foran ek secure Cloudflare Public HTTPS link de dega.
- Active Live Link:
  **`https://wars-covering-wrestling-typically.trycloudflare.com`**

---

## 🌟 Main Features & Capabilities

### 1. File Upload (Single ya 100 Files Batch)
- Ek waqt mein single assignment ya **100 files ek sath drag & drop** kar ke upload karein.
- Har file ka size aur status queue mein nazar aata hai.
- "Load Unit 1 Sample (.docx)" button se foran test assignment load kar ke check kar sakte hain.

### 2. Unicode Character Replacements (Homoglyphs)
- **Default 6 Homoglyphs (Preset):**
  - `l` → `ӏ` (U+04CF - Cyrillic Small Letter Palochka)
  - `k` → `κ` (U+03BA - Greek Small Letter Kappa)
  - `d` → `ԁ` (U+0501 - Cyrillic Small Letter Komi De)
  - `e` → `е` (U+0435 - Cyrillic Small Letter Ie)
  - `p` → `р` (U+0440 - Cyrillic Small Letter Er)
  - `q` → `զ` (U+0566 - Armenian Small Letter Za)
- **Extended Presets:** `a → а`, `c → с`, `o → о`, `s → ѕ`, `y → у`, `x → х`, `i → і`, `j → ј`.
- **Custom Character Addition:** Kisi bhi custom character ko find aur replace mein daal kar add karein (Unicode Hex Code auto-detect hota hai).
- Har character ko individual on/off switch se control kiya ja sakta hai.

### 3. Formatting & Scope Controls (No Layout Distortion)
- **Keep Cover Sheet Untouched (Recommended):**
  - College logos, Qualification tables, Learner Details, Statement of Authenticity aur Table of Contents ko bilkul untouched rakhta hai.
  - Unicode replacements sirf main body (`Introduction:` se aagay) par apply hoti hain.
- **Remove Cover Sheet & TOC:**
  - Cover Sheet aur Table of Contents ko cleanly remove kar deta hai.
  - Document seedha Page 1 par Introduction se start hota hai.
- **Entire Document:** Poore document par replacements apply karta hai.
- **Skip Web URLs (Checked by Default):**
  - Bibliography aur citations mein `http://`, `https://`, aur `www.` links ko detect kar ke safe rakhta hai taake URLs kharab na hon aur valid rahein.
- **Skip Main Headings:** Headings (Introduction, Task 1, Conclusion waghera) ko standard English mein chhor sakta hai.

### 4. Live Preview & Statistics
- **Highlighted Text Diff Tab:** Replaced characters ko distinct badge/highlight ke sath show karta hai taake har tabdeeli saaf nazar aaye.
- **Original Layout PDF Preview Tab:** Vector PDF ka high-resolution page render display karta hai taake aap college logos, tables aur headers ko verify kar sakein.
- **Live Counters:**
  - Har character ka alag alag count (e.g. `l: 620`, `k: 96`, `d: 565`, `e: 1,615`, `p: 296`, `q: 20`).
  - Total replacements aur total word count.
- **Weekly Target Tracker:** Haftay ke 100 PDFs target ko track karne ke liye visual progress bar.

### 5. Download & Export
- **Download Selectable PDF:** Real selectable-text vector PDF with 100% intact formatting.
- **Download .DOCX:** Transformed Word document.
- **Batch All → ZIP:** Tamam uploaded files (10 to 100 files) ko aik click mein convert kar ke single `.zip` file mein download deta hai.

---

## ❓ Pehli HTML File mein Formatting kyun kharab ho rahi thi?

Pehle wali HTML file (`unicode_assignment_transformer_pdf_studio.html`) browser JavaScript (`pdfmake` / `mammoth`) use kar rahi thi. Browser JS Word ke complex XML features ko render nahi kar sakta:
1. `pdfmake` ne tables ke column widths ko divide kar ke barabar kar diya tha (`widths: '*'`), jis se Cover sheet ke tables shrink aur distort ho gaye.
2. Word ke headers, footers (`word/header1.xml`) aur exact page margins browser JS mein strip ho jate the.
3. College logos ke dimensions kharab ho jate the.

**Is nayi Web App mein yeh masla kaise hal hua?**
- Nayi Web App backend par OpenXML structure ke sirf text elements (`<w:t>`) ko update karti hai, jabke table layout, borders, font styles, logos, headers aur margins ko 100% untouched rakhti hai.
- PDF conversion aapke system par mojood **Microsoft Word / LibreOffice headless engine** se hoti hai, jo 1:1 pixel-perfect original formatting aur asali selectable-text PDF generate karta hai.
