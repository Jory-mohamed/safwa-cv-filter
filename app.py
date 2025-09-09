# app.py
import streamlit as st
from io import BytesIO
from pathlib import Path

from PyPDF2 import PdfReader
import docx2txt
from rapidfuzz import fuzz

# ========= إعدادات عامة =========
THRESH = 80  # نسبة التطابق المطلوبة (غيّريها لو حبيتي)
st.set_page_config(page_title="صفوة لفرز السير الذاتية", layout="centered")
st.title("صفوة لفرز السير الذاتية")

# ========= دوال مساعدة =========
AR_DIACS = "".join([
    "\u064B","\u064C","\u064D","\u064E","\u064F","\u0650","\u0651","\u0652",
    "\u0653","\u0654","\u0655","\u0670","\u0640"  # التشكيل + التطويل
])

def normalize_ar(s: str) -> str:
    if not s: return ""
    s = s.replace("أ","ا").replace("إ","ا").replace("آ","ا")
    s = s.replace("ى","ي").replace("ؤ","و").replace("ئ","ي").replace("ة","ه")
    s = "".join(ch for ch in s if ch not in AR_DIACS)
    return s.lower().strip()

def read_pdf(file) -> str:
    try:
        reader = PdfReader(file)
        pages = []
        for p in reader.pages:
            try:
                pages.append(p.extract_text() or "")
            except Exception:
                pages.append("")
        return "\n".join(pages)
    except Exception:
        try:
            data = file.read()
            file.seek(0)
            reader = PdfReader(BytesIO(data))
            return "\n".join([(p.extract_text() or "") for p in reader.pages])
        except Exception:
            return ""

def read_docx(file) -> str:
    # ملاحظة: docx2txt يفضّل مسار ملف؛ أحياناً يرجّع نص فارغ على السحابة.
    # نجربه مباشرة، وإذا فشل نرجّع نصًا فارغًا.
    try:
        return docx2txt.process(file) or ""
    except Exception:
        return ""

def read_txt(file) -> str:
    try:
        return file.read().decode("utf-8", errors="ignore")
    except Exception:
        try:
            return file.read().decode("cp1256", errors="ignore")
        except Exception:
            return ""

def read_file_text(up):
    name = (up.name or "").lower()
    if name.endswith(".pdf"):
        return read_pdf(up)
    if name.endswith(".docx"):
        return read_docx(up)
    if name.endswith(".txt"):
        return read_txt(up)
    return ""

def parse_keywords(s: str):
    if not s: return []
    parts = [p.strip() for p in s.replace("|",",").replace("/",",").split(",")]
    return [p for p in parts if p]

# fuzzy helper: نتحقق أولاً من وجود تطابق حرفي، وإلا نستخدم partial_ratio
def fuzzy_contains(text_norm: str, query_norm: str, thresh: int = THRESH) -> bool:
    if not query_norm:
        return True
    if query_norm in text_norm:
        return True
    # rapidfuzz.partial_ratio سريع ومناسب للجمل القصيرة ضد نص طويل
    score = fuzz.partial_ratio(text_norm, query_norm)
    return score >= thresh

NATION_SYNONYMS = {
    "saudi": {
        "سعودي","سعوديه","سعودية","سعود","مواطن سعودي",
        "ksa","saudi","saudi arabia","sa"
    },
    "non": {
        "غير سعودي","غير سعوديه","غير-سعودي","غيرسعودي",
        "non saudi","non-saudi","foreigner","expat"
    }
}

def match_nation(text_norm: str, want_raw: str, thresh: int = THRESH) -> bool:
    if not want_raw.strip():
        return True
    want = normalize_ar(want_raw)
    # تحديد المجموعة
    if "سعود" in want or "ksa" in want or "saudi" in want:
        group = "saudi"
    elif "غير" in want or "non" in want:
        group = "non"
    else:
        # كلمة حرّة: نستخدم fuzzy
        return fuzzy_contains(text_norm, want, thresh)
    # مرادفات
    for cand in NATION_SYNONYMS[group]:
        if fuzzy_contains(text_norm, normalize_ar(cand), thresh):
            return True
    return False

# ========= واجهة الإدخال =========
col1, col2 = st.columns(2)
with col1:
    uni = st.text_input("الجامعة", placeholder="مثال: جامعة الملك سعود")
with col2:
    major = st.text_input("التخصص", placeholder="مثال: نظم معلومات إدارية")

nation = st.text_input("الجنسية", placeholder="مثال: سعودي / Non-Saudi")
extra  = st.text_input("كلمات إضافية (اختياري)", placeholder="مثال: خبرة، تدريب صيفي")

uploads = st.file_uploader(
    "ارفاق ملفات CV (PDF / DOCX / TXT)",
    type=["pdf","docx","txt"],
    accept_multiple_files=True
)

# اختيار العتبة من الواجهة (اختياري)
THRESH = st.slider("نسبة المطابقة (Fuzzy)", 60, 100, THRESH, step=1)

if st.button("ابدأ الفرز الآن"):
    if not uploads:
        st.warning("حمّلي ملف واحد على الأقل.")
    else:
        uni_n   = normalize_ar(uni)
        major_n = normalize_ar(major)
        extra_keys = [normalize_ar(k) for k in parse_keywords(extra)]
        nation_raw = nation

        for up in uploads:
            content = read_file_text(up)
            content_n = normalize_ar(content)

            # نبني الشروط (الموجود فقط)
            checks = []
            if uni_n:
                checks.append(fuzzy_contains(content_n, uni_n, THRESH))
            if major_n:
                checks.append(fuzzy_contains(content_n, major_n, THRESH))
            if nation_raw.strip():
                checks.append(match_nation(content_n, nation_raw, THRESH))
            for k in extra_keys:
                checks.append(fuzzy_contains(content_n, k, THRESH))

            ok = all(checks) if checks else False

            if ok:
                st.success(f"✅ مطابق: {up.name}")
            else:
                st.error(f"❌ غير مطابق: {up.name}")