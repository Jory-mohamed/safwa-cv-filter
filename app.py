# app.py
import streamlit as st
from io import BytesIO
from pathlib import Path
import tempfile
import os

from PyPDF2 import PdfReader
import docx2txt
from rapidfuzz import fuzz

# ====== إعدادات ثابتة (ثبّتنا العتبة على 80 ومخفّين التحكم) ======
THRESH = 80  # لا تغيّري من واجهة المستخدم — ثابت
st.set_page_config(page_title="صفوة لفرز السير الذاتية", layout="centered")
st.title("صفوة لفرز السير الذاتية")

# ====== دوال مساعدة ======
AR_DIACS = "".join([
    "\u064B","\u064C","\u064D","\u064E","\u064F","\u0650","\u0651","\u0652",
    "\u0653","\u0654","\u0655","\u0670","\u0640"
])

def normalize_ar(s: str) -> str:
    if not s: return ""
    s = s.replace("أ","ا").replace("إ","ا").replace("آ","ا")
    s = s.replace("ى","ي").replace("ؤ","و").replace("ئ","ي").replace("ة","ه")
    s = "".join(ch for ch in s if ch not in AR_DIACS)
    return s.lower().strip()

def read_pdf_file(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(file_bytes))
        pages = []
        for p in reader.pages:
            pages.append(p.extract_text() or "")
        return "\n".join(pages)
    except Exception:
        return ""

def read_docx_file_bytes(file_bytes: bytes) -> str:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        text = docx2txt.process(tmp_path) or ""
    except Exception:
        text = ""
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
    return text

def read_txt_bytes(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        try:
            return file_bytes.decode("cp1256", errors="ignore")
        except Exception:
            return ""

def read_uploaded_file(up):
    name = (up.name or "").lower()
    data = up.read()
    up.seek(0)
    if name.endswith(".pdf"):
        return read_pdf_file(data)
    if name.endswith(".docx"):
        return read_docx_file_bytes(data)
    if name.endswith(".txt"):
        return read_txt_bytes(data)
    return ""

def fuzzy_contains(text_norm: str, query_norm: str, thresh: int = THRESH) -> bool:
    if not query_norm:
        return True
    if query_norm in text_norm:
        return True
    score = fuzz.partial_ratio(text_norm, query_norm)
    return score >= thresh

# خريطة مرادفات بسيطة للجنسية (نقدر نضيف بعدها)
NATION_SYNONYMS = {
    "saudi": ["سعودي", "سعوديه", "سعودية", "ksa", "saudi"],
    "non": ["غير سعودي", "non saudi", "foreigner", "expat"]
}

def match_nation(text_norm: str, want_raw: str) -> bool:
    if not want_raw.strip():
        return True
    w = normalize_ar(want_raw)
    if "غير" in w or "non" in w:
        group = "non"
    elif "سعود" in w or "ksa" in w or "saudi" in w:
        group = "saudi"
    else:
        return fuzzy_contains(text_norm, w, THRESH)
    for cand in NATION_SYNONYMS.get(group, []):
        if fuzzy_contains(text_norm, normalize_ar(cand), THRESH):
            return True
    return False

# ====== واجهة المستخدم ======
col1, col2 = st.columns(2)
with col1:
    uni = st.text_input("الجامعة", placeholder="مثال: جامعة الملك سعود")
with col2:
    major = st.text_input("التخصص", placeholder="مثال: نظم معلومات إدارية")

nation = st.text_input("الجنسية", placeholder="مثال: سعودي / Non-Saudi")
extra  = st.text_input("كلمات إضافية (اختياري)", placeholder="مثال: خبرة، تدريب صيفي")

uploads = st.file_uploader(
    "ارفاق ملفات CV (PDF / DOCX / TXT) — اسحب أكثر من ملف معًا",
    type=["pdf","docx","txt"],
    accept_multiple_files=True
)

# زر التشغيل
if st.button("ابدأ الفرز الآن"):
    if not uploads:
        st.warning("حمّلي ملف واحد على الأقل.")
    else:
        uni_n   = normalize_ar(uni)
        major_n = normalize_ar(major)
        extra_keys = [normalize_ar(k) for k in (extra or "").replace("|",",").replace("/",",").split(",") if k.strip()]
        nation_raw = nation or ""

        for up in uploads:
            content = read_uploaded_file(up)
            content_n = normalize_ar(content)

            checks = []
            if uni_n:
                checks.append(fuzzy_contains(content_n, uni_n, THRESH))
            if major_n:
                checks.append(fuzzy_contains(content_n, major_n, THRESH))
            if nation_raw.strip():
                checks.append(match_nation(content_n, nation_raw))
            for k in extra_keys:
                checks.append(fuzzy_contains(content_n, k, THRESH))

            ok = all(checks) if checks else False

            if ok:
                st.success(f"✅ مطابق: {up.name}")
            else:
                st.error(f"❌ غير مطابق: {up.name}")