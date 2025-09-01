import streamlit as st
import pandas as pd
import re
from fuzzywuzzy import fuzz
from PyPDF2 import PdfReader

# ==============================
# 1) دوال مساعدة لمعالجة النص
# ==============================
def normalize_arabic(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r'[\u0617-\u061A\u064B-\u0652\u0670]', '', s)
    s = s.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
    s = s.replace('ى', 'ي').replace('يٰ', 'ي')
    s = s.replace('ؤ', 'و').replace('ئ', 'ي')
    s = s.replace('ة', 'ه')
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def keep_arabic_space(s: str) -> str:
    return re.sub(r'[^\u0600-\u06FF ]+', ' ', s)

def per_word_scores(phrase: str, text: str):
    words = [w for w in normalize_arabic(phrase).lower().split() if w]
    scores = [fuzz.partial_ratio(w, text) for w in words]
    return words, scores

# ==============================
# 2) دوال التحقق
# ==============================
def decide_university(phrase: str, text: str, thresh: int = 60):
    words, scores = per_word_scores(phrase, text)
    avg = (sum(scores)/len(scores)) if scores else 0
    min_word = min(scores) if scores else 0
    return (avg >= thresh or min_word >= thresh)

def decide_major(phrase: str, text: str, thresh: int = 60):
    words = [w for w in normalize_arabic(phrase).lower().split() if w]
    found_count = 0
    for w in words:
        sc = fuzz.partial_ratio(w, text)
        if sc >= thresh:
            found_count += 1
    if len(words) >= 3:
        need = 2
    else:
        need = len(words)
    return found_count >= need

def gen_nat_variants(word: str):
    w = normalize_arabic(word).lower()
    vars_ = {w}
    if w.startswith('ال'): vars_.add(w[2:])
    if w.endswith('ي'): vars_.add(w + 'ه')   # سعودي -> سعوديه
    if w.endswith('يه'): vars_.add(w[:-1])   # سعوديه -> سعودي
    return list(vars_)

def decide_nationality(phrase: str, text: str, thresh: int = 70):
    base = [w for w in normalize_arabic(phrase).lower().split() if w]
    cands = set()
    for w in base:
        for v in gen_nat_variants(w):
            cands.add(v)
    scores = {w: fuzz.partial_ratio(w, text) for w in cands}
    return any(s >= thresh for s in scores.values())

# ==============================
# 3) واجهة المستخدم
# ==============================
st.set_page_config(page_title="صفوة - فلترة السير الذاتية", layout="centered")

st.title("📄 صفوة - فلترة السير الذاتية")

# إدخال المستخدم
st.sidebar.header("⚙️ خيارات الفلترة")
uni_input = st.sidebar.text_input("ادخل اسم الجامعة", "جامعة الملك سعود")
major_input = st.sidebar.text_input("ادخل اسم التخصص", "نظم المعلومات الادارية")
nat_input = st.sidebar.text_input("ادخل الجنسية", "سعودي / سعودية")

uploaded_files = st.file_uploader("✨ ارفع ملفات السير الذاتية (PDF)", type="pdf", accept_multiple_files=True)

if st.button("تشغيل الفلتر الآن"):
    if not uploaded_files:
        st.warning("⚠️ الرجاء رفع ملفات PDF أولاً.")
    else:
        rows = []
        for file in uploaded_files:
            reader = PdfReader(file)
            raw_text = ""
            for page in reader.pages:
                raw_text += page.extract_text() or ""

            text_norm = normalize_arabic(keep_arabic_space(raw_text)).lower()

            uni_found = decide_university(uni_input, text_norm)
            major_found = decide_major(major_input, text_norm)
            nat_found = decide_nationality(nat_input, text_norm)

            status = "✅ مقبول" if (uni_found and major_found and nat_found) else "❌ مرفوض"

            rows.append({
                "الملف": file.name,
                "الجامعة": "صح" if uni_found else "خطأ",
                "التخصص": "صح" if major_found else "خطأ",
                "الجنسية": "صح" if nat_found else "خطأ",
                "الحالة": status
            })

        df = pd.DataFrame(rows)
        st.subheader("📊 النتائج")
        st.dataframe(df, use_container_width=True)

        st.download_button(
            "⬇️ تحميل النتائج كـ CSV",
            df.to_csv(index=False, encoding="utf-8-sig"),
            "results.csv",
            "text/csv",
            key="download-csv"
        )
