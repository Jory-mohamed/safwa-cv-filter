# app.py
import streamlit as st
from pathlib import Path
import pdfplumber
import docx2txt
from rapidfuzz import fuzz

# -------- إعدادات الصفحة --------
st.set_page_config(page_title="صفوة لفرز السير الذاتية", page_icon=":mag:")
st.title("📄 صفوة لفرز السير الذاتية")

# -------- دوال مساعدة --------
def normalize_text(text: str) -> str:
    """تنظيف النص من الرموز الغريبة وتوحيد الشكل"""
    if not text:
        return ""
    text = text.lower()
    text = text.replace("ة", "ه").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = "".join(ch for ch in text if ch.isalnum() or ch.isspace())
    return text

def extract_text(file) -> str:
    """محاولة استخراج النص من PDF أو DOCX"""
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

# -------- الواجهة --------
st.write("✨ حمّل سيرتك الذاتية بصيغة PDF أو DOCX أو XLSX")

uploaded_file = st.file_uploader("إرفع الملف", type=["pdf", "docx", "xlsx"])

university_input = st.text_input("الجامعة")
major_input = st.text_input("التخصص")
nation_input = st.text_input("الجنسية")

if uploaded_file is not None:
    text = extract_text(uploaded_file)

    uni = normalize_text(university_input)
    major = normalize_text(major_input)
    nation = normalize_text(nation_input)

    THRESH = 80  # النسبة الثابتة

    uni_score = fuzz.partial_ratio(uni, text) if uni else 100
    major_score = fuzz.partial_ratio(major, text) if major else 100
    nation_score = fuzz.partial_ratio(nation, text) if nation else 100

    # التحقق النهائي
    if min(uni_score, major_score, nation_score) >= THRESH:
        st.success(f"✅ مطابق للشروط: {uploaded_file.name}")
    else:
st.error(f"❌ غير مطابق (واحد أو أكثر أقل من {THRESH}%)")