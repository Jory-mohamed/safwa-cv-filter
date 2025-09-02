import streamlit as st
import re
import unicodedata
from pypdf import PdfReader
import io

st.set_page_config(page_title="فرز السير الذاتية - HR Filter", page_icon="🗂️")
st.title("🗂️ برنامج فرز السير الذاتية (نسخة تجريبية)")
st.write("يتحقق من: **جامعة الملك سعود** + **نظم المعلومات الإدارية** + **الجنسية السعودية**")

# --------- Utilities ---------
def normalize_ar(text: str) -> str:
    if not text:
        return ""
    # lowercase
    text = text.lower()
    # remove diacritics
    text = ''.join(ch for ch in unicodedata.normalize('NFKD', text) if not unicodedata.combining(ch))
    # normalize common Arabic letters
    text = re.sub(r"[أإآٱ]", "ا", text)
    text = text.replace("ة", "ه").replace("ى", "ي")
    # remove extra spaces/punct
    text = re.sub(r"[^0-9a-z\u0600-\u06FF\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for p in reader.pages:
        try:
            pages.append(p.extract_text() or "")
        except Exception:
            pages.append("")
    return "\n".join(pages)

# --------- Rule Set (بسيطة وواضحة) ---------
UNI_PATTERNS = [
    r"\bجامعه?\s+الملك\s+سعود\b",      
    r"\bking\s+saud\s+university\b",     
    r"\bksu\b"
]
MAJOR_PATTERNS = [
    r"\bنظم\s+المعلومات\s+الاداري[ه|ة]\b",
    r"\bmis\b",
    r"\bmanagement\s+information\s+systems?\b"
]
NAT_PATTERNS = [
    r"\bسعودي(ه)?\b",
    r"\bsaudi( arabia| national)?\b"
]

def match_any(patterns, text):
    return any(re.search(p, text) for p in patterns)

def evaluate_cv(text_raw: str):
    text = normalize_ar(text_raw)
    uni_ok   = match_any(UNI_PATTERNS, text)
    major_ok = match_any(MAJOR_PATTERNS, text)
    nat_ok   = match_any(NAT_PATTERNS, text)

    all_ok = uni_ok and major_ok and nat_ok
    verdict = "✅ صح (مطابق للشروط)" if all_ok else "❌ خطأ (غير مطابق)"
    reasons = []
    reasons.append(f"الجامعة: {'✅ موجود' if uni_ok else '❌ غير موجود'}")
    reasons.append(f"التخصص: {'✅ موجود' if major_ok else '❌ غير موجود'}")
    reasons.append(f"الجنسية: {'✅ موجود' if nat_ok else '❌ غير موجود'}")
    return verdict, reasons

# --------- UI ---------
tab1, tab2 = st.tabs(["تحقق من سيرة ذاتية واحدة", "عدة سير ذاتية (تجربة سريعة)"])

with tab1:
    st.subheader("ادخلي النص مباشرة أو ارفعي PDF")
    cv_text = st.text_area("ألصقي نص السيرة الذاتية هنا:", height=200, placeholder="الاسم ... الجامعة ... التخصص ... الجنسية ...")
    uploaded = st.file_uploader("أو ارفعي ملف PDF", type=["pdf"])

    if st.button("تحقّق الآن"):
        if uploaded and not cv_text.strip():
            try:
                raw = extract_pdf_text(uploaded.read())
            except Exception as e:
                st.error(f"تعذّر قراءة الـ PDF: {e}")
                raw = ""
        else:
            raw = cv_text

        if not raw.strip():
            st.warning("فضلاً ضعي نصاً أو ارفعي PDF.")
        else:
            verdict, reasons = evaluate_cv(raw)
            st.markdown(f"### النتيجة: {verdict}")
            st.write("**التفصيل:**")
            for r in reasons:
                st.write("- " + r)

with tab2:
    st.subheader("اختبار سريع بعينات (نصوص قصيرة)")
    sample_1 = "الجامعه: جامعة الملك سعود\nالتخصص: نظم المعلومات الادارية\nالجنسيه: سعوديه"
    sample_2 = "University: King Saud University\nMajor: MIS\nNationality: Saudi"
    sample_3 = "الجامعة: جامعة الملك خالد\nالتخصص: محاسبة\nالجنسية: غير سعودي"

    col1, col2, col3 = st.columns(3)
    for i, s in enumerate([sample_1, sample_2, sample_3], start=1):
        with [col1, col2, col3][i-1]:
            st.code(s, language="text")
            v, rs = evaluate_cv(s)
            st.write(f"**النتيجة:** {v}")
            for r in rs:
                st.caption(r)

st.caption("نسخة تجريبية — المطابقة تعتمد على النص المستخرج؛ دقة PDF تتأثر بطريقة كتابة الملف.")
