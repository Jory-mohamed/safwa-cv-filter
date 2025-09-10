import streamlit as st
import pdfplumber
import docx2txt
from rapidfuzz import fuzz
from io import BytesIO

st.set_page_config(page_title="صفوة لفرز السير الذاتية", layout="centered")
st.title("📄 صفوة لفرز السير الذاتية")
st.caption("تميّز بخطوة — نسخة محسّنة")

# ---------------- دوال مساعدة ----------------
def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = text.replace("ة","ه").replace("أ","ا").replace("إ","ا").replace("آ","ا")
    text = "".join(ch for ch in text if ch.isalnum() or ch.isspace())
    return text

def extract_text(file) -> str:
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

def best_score(needle: str, haystack: str) -> int:
    """نستخدم token_sort_ratio عشان يقارن حتى لو الكلمات متلخبطة"""
    if not needle:
        return 100
    n = normalize_text(needle)
    h = normalize_text(haystack)
    return fuzz.token_sort_ratio(n, h)

def nationality_synonyms(nation: str):
    """مرادفات الجنسية"""
    n = normalize_text(nation)
    if not n:
        return []
    if "غير" in n or "وافد" in n or "non" in n:
        return ["غير سعودي","غيرسعودي","non saudi","nonsaudi","expat","وافد"]
    return ["سعودي","سعوديه","saudi","ksa","saudi arabia"]

# ---------------- الواجهة ----------------
col1, col2 = st.columns(2)
with col1:
    university_input = st.text_input("الجامعة", placeholder="مثال: جامعة الملك سعود")
with col2:
    major_input = st.text_input("التخصص", placeholder="مثال: نظم معلومات إدارية")

nation_input = st.text_input("الجنسية", placeholder="مثال: سعودي")

uploaded_file = st.file_uploader("✨ ارفع سيرتك الذاتية (PDF أو DOCX)", type=["pdf","docx"])

THRESH = 80  # ثابت

if uploaded_file is not None:
    text = extract_text(uploaded_file)

    uni_score = best_score(university_input, text)
    major_score = best_score(major_input, text)

    nat_scores = []
    if nation_input.strip():
        for syn in nationality_synonyms(nation_input):
            nat_scores.append(best_score(syn, text))
    else:
        nat_scores = [100]
    nation_score = max(nat_scores)

    # عرض النتائج
    colA, colB, colC = st.columns(3)
    colA.metric("الجامعة", f"{uni_score}%")
    colB.metric("التخصص", f"{major_score}%")
    colC.metric("الجنسية", f"{nation_score}%")

    if all([uni_score>=THRESH, major_score>=THRESH, nation_score>=THRESH]):
        st.success(f"✅ مطابق للشروط: {uploaded_file.name}")
    else:
        st.error(f"❌ غير مطابق (أحد الشروط أقل من {THRESH}%)")