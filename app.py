import streamlit as st
import pandas as pd
import io, re, zipfile
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pdfplumber
import arabic_reshaper
from bidi.algorithm import get_display
from rapidfuzz import fuzz

# OCR
import pytesseract
from PIL import Image
import fitz  # PyMuPDF

# ── إعداد الصفحة ───────────────────────────────────────────────
st.set_page_config(page_title="صفوة | فرز السير الذاتية", page_icon="🔎", layout="centered")

# أجبر الخلفية تكون بيضاء دائمًا
st.markdown("""
<style>
body, .stApp {
    background-color: #FFFFFF !important;
    color: #111111 !important;
}
.block-container {
    padding-top: 2rem; max-width: 900px;
}
h1,h2,h3 { color: #0F1A2E; }
.stTextInput>div>div>input {
    background: #FAF3E8 !important;  /* كريمي */
    color: #111111 !important;
    border-radius: 12px;
}
.stFileUploader>div {
    background: #FAF3E8 !important;  /* كريمي */
    border-radius: 12px;
}
.stButton>button {
    background: #0F1A2E;  /* كحلي */
    color: #FFFFFF;
    border-radius: 12px;
    font-weight: 600;
    height: 44px;
}
</style>
""", unsafe_allow_html=True)

# ── دوال مساعدة ────────────────────────────────────────────────
ARABIC_DIACRITICS = re.compile(r'[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]')

def normalize_arabic(s: str) -> str:
    if not s: return ""
    s = s.strip()
    s = ARABIC_DIACRITICS.sub('', s)
    s = (s.replace('أ','ا').replace('إ','ا').replace('آ','ا')
           .replace('ى','ي').replace('ئ','ي').replace('ؤ','و').replace('ة','ه'))
    s = re.sub(r'\s+', ' ', s)
    return s

def fuzzy_score(needle: str, haystack: str) -> int:
    if not needle or not haystack: return 0
    return fuzz.partial_ratio(needle.lower(), haystack.lower())

def read_txt(file) -> str:
    try:
        data = file.read()
        for enc in ("utf-8", "windows-1256", "latin-1"):
            try: return data.decode(enc, errors="ignore")
            except Exception: continue
        return data.decode("utf-8", errors="ignore")
    except Exception: return ""

def read_docx(file) -> str:
    try:
        data = file.read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            with z.open('word/document.xml') as d:
                xml = d.read().decode('utf-8', errors='ignore')
        text = re.sub(r'</w:p>', '\n', xml)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text
    except Exception: return ""

def read_pdf_arabic(file) -> str:
    try:
        data = file.read()
        out = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for p in pdf.pages:
                t = p.extract_text() or ""
                t = re.sub(r'\s+', ' ', t)
                t = get_display(arabic_reshaper.reshape(t))
                out.append(t)
        return normalize_arabic("\n".join(out))
    except Exception:
        return ""

def read_pdf_ocr(file) -> str:
    """OCR احتياطي للـPDF باستخدام Tesseract"""
    try:
        data = file.read()
        doc = fitz.open(stream=data, filetype="pdf")
        texts = []
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            t = pytesseract.image_to_string(img, lang="ara+eng")
            texts.append(t)
        return normalize_arabic("\n".join(texts))
    except Exception:
        return ""

def read_xlsx(file) -> str:
    try:
        df = pd.read_excel(file).fillna("")
        return " ".join(df.astype(str).values.ravel().tolist())
    except Exception:
        return ""

def get_file_text(sf, use_ocr=False) -> str:
    name = (sf.name or "").lower()
    sf.seek(0)
    if name.endswith(".txt"):
        return normalize_arabic(read_txt(sf))
    if name.endswith(".docx"):
        sf.seek(0); return normalize_arabic(read_docx(sf))
    if name.endswith(".pdf"):
        sf.seek(0)
        txt = read_pdf_arabic(sf)
        if (not txt or len(txt) < 30) and use_ocr:
            sf.seek(0)
            return read_pdf_ocr(sf)
        return txt
    if name.endswith(".xlsx"):
        sf.seek(0); return normalize_arabic(read_xlsx(sf))
    return normalize_arabic(name)

def file_size_kb(sf) -> int:
    try:
        sf.seek(0, 2); size = sf.tell(); sf.seek(0); return int(size/1024)
    except Exception: return 0

# ── الواجهة ─────────────────────────────────────────────────────
st.markdown("## صفوة – فرز السير الذاتية 🔎")
st.caption("املئي الحقول، ارفعي الملفات، واضغطي «فرّز». النتائج تصدر CSV/XLSX/PDF.")

with st.form("filter_form", clear_on_submit=False):
    university = st.text_input("الجامعة", placeholder="مثال: جامعة الملك سعود / KSU")
    major      = st.text_input("التخصص", placeholder="مثال: نظم المعلومات الإدارية / MIS")
    nationality= st.text_input("الجنسية", placeholder="مثال: سعودي/سعودية")
    uploaded = st.file_uploader(
        "ارفعي السير الذاتية (PDF / DOCX / TXT / XLSX)",
        type=["pdf","docx","txt","xlsx"], accept_multiple_files=True
    )
    use_ocr = st.checkbox("تفعيل OCR للـPDF عند الحاجة", value=True)
    submitted = st.form_submit_button("فرّز ✅")

THRESHOLD = 80

if submitted:
    if not uploaded:
        st.warning("ارفعي ملفات أولًا.")
    else:
        uni_q = normalize_arabic(university)
        maj_q = normalize_arabic(major)
        nat_q = normalize_arabic(nationality)

        rows, errors = [], []

        for f in uploaded:
            try:
                ext = (f.name.split(".")[-1]).lower() if "." in f.name else ""
                text = get_file_text(f, use_ocr=use_ocr)

                uni_score = fuzzy_score(uni_q, text) if uni_q else 0
                maj_score = fuzzy_score(maj_q, text) if maj_q else 0
                nat_score = fuzzy_score(nat_q, text) if nat_q else 0

                hits = sum(s >= THRESHOLD for s in [uni_score, maj_score, nat_score])
                if hits == 3:
                    decision = "مطابق قوي"
                elif hits == 2:
                    decision = "مطابق مبدئي"
                else:
                    decision = "غير مطابق"

                rows.append({
                    "الملف": f.name,
                    "النوع": ext.upper(),
                    "الحجم KB": file_size_kb(f),
                    "درجة الجامعة": uni_score,
                    "درجة التخصص": maj_score,
                    "درجة الجنسية": nat_score,
                    "عدد التطابقات": hits,
                    "القرار": decision
                })
            except Exception as e:
                errors.append(f"تعذّر معالجة {f.name}: {e}")

        if errors:
            st.info("بعض الملفات لم تُعالج:")
            for msg in errors: st.caption(f"• {msg}")

        if rows:
            results_df = pd.DataFrame(rows)
            st.dataframe(results_df, use_container_width=True)

            # تنزيل CSV
            csv_buf = io.StringIO()
            results_df.to_csv(csv_buf, index=False)
            st.download_button("⬇️ CSV", data=csv_buf.getvalue().encode("utf-8-sig"),
                file_name=f"results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv")

            # تنزيل XLSX
            xlsx_buf = io.BytesIO()
            with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
                results_df.to_excel(writer, index=False, sheet_name="Results")
            st.download_button("⬇️ Excel (XLSX)", data=xlsx_buf.getvalue(),
                file_name=f"results_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            # تنزيل PDF
            pdf_buf = io.BytesIO()
            with PdfPages(pdf_buf) as pdf:
                fig, ax = plt.subplots(figsize=(11.69, 8.27))
                ax.axis('off')
                ax.set_title("تقرير فرز السير الذاتية — صفوة", fontsize=14, pad=14)
                table = ax.table(cellText=results_df.values, colLabels=results_df.columns,
                                 loc='center', cellLoc='center')
                table.auto_set_font_size(False); table.set_fontsize(7); table.scale(1, 1.2)
                pdf.savefig(fig, bbox_inches='tight'); plt.close(fig)
            st.download_button("⬇️ PDF", data=pdf_buf.getvalue(),
                file_name=f"results_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf")
        else:
            st.warning("ما في نتائج لعرضها.")