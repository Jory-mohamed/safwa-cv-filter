import streamlit as st
import pdfplumber
import docx2txt
from rapidfuzz import fuzz
from io import BytesIO

# -------- إعدادات الصفحة --------
st.set_page_config(page_title="صفوة لفرز السير الذاتية", page_icon=":mag:", layout="centered")
st.title("📄 صفوة لفرز السير الذاتية")
st.caption("تميّز بخطوة")

# -------- دوال مساعدة --------
def normalize_text(text: str) -> str:
    """تنظيف النص وتوحيد الأشكال"""
    if not text:
        return ""
    text = text.lower()
    text = text.replace("ة", "ه").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = "".join(ch for ch in text if ch.isalnum() or ch.isspace())
    return text

def extract_text(file) -> str:
    """استخراج النصوص من PDF أو DOCX"""
    text = ""
    if file.name.endswith(".pdf"):
        try:
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        except:
            text = ""
    elif file.name.endswith(".docx"):
        try:
            text = docx2txt.process(file)
        except:
            text = ""
    return normalize_text(text)

def fuzzy_match(needle: str, haystack: str, threshold: int = 80) -> bool:
    """مطابقة Fuzzy بنسبة ثابتة"""
    if not needle:
        return True
    score = fuzz.partial_ratio(normalize_text(needle), normalize_text(haystack))
    return score >= threshold

# -------- الواجهة --------
col1, col2 = st.columns(2)
with col1:
    university_input = st.text_input("الجامعة", placeholder="مثال: جامعة الملك سعود")
with col2:
    major_input = st.text_input("التخصص", placeholder="مثال: نظم معلومات إدارية")

nation_input = st.text_input("الجنسية", placeholder="مثال: سعودي")

uploaded_file = st.file_uploader("✨ ارفع سيرتك الذاتية (PDF أو DOCX)", type=["pdf", "docx"])

if uploaded_file is not None:
    text = extract_text(uploaded_file)

    THRESH = 80  # النسبة ثابتة ومخفية

    uni_ok = fuzzy_match(university_input, text, THRESH)
    major_ok = fuzzy_match(major_input, text, THRESH)
    nation_ok = fuzzy_match(nation_input, text, THRESH)

    if all([uni_ok, major_ok, nation_ok]):
        st.success(f"✅ مطابق للشروط: {uploaded_file.name}")
    else:
        st.error(f"❌ غير مطابق (واحد أو أكثر أقل من {THRESH}%)")