# -*- coding: utf-8 -*-
# صفوة لفرز السير الذاتية – نسخة نهائية

import io
from pathlib import Path

import streamlit as st
from rapidfuzz import fuzz

# ===== إعداد عام =====
st.set_page_config(
    page_title="صفوة لفرز السير الذاتية",
    page_icon="🔎",
    layout="centered"
)

# تحميل CSS مخصص (اختياري)
css_path = Path("static/style.css")
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# ثابت المطابقة (مخفي)
THRESH = 80

# ===== رأس الصفحة (لوقو + عنوان) =====
logo_path = Path("static/logo.png")
if logo_path.exists():
    st.image(str(logo_path), width=140)
st.markdown(
    "<h1 class='page-title'>صفوة لفرز السير الذاتية</h1>"
    "<p class='tagline'>تميّز بخطوة</p>",
    unsafe_allow_html=True,
)

# ===== الحقول =====
col1, col2 = st.columns(2)
with col1:
    uni = st.text_input("الجامعة", placeholder="مثال: جامعة الملك سعود")
with col2:
    major = st.text_input("التخصص", placeholder="مثال: نظم المعلومات الإدارية")

nation = st.text_input("الجنسية", placeholder="مثال: سعودي / غير سعودي")
st.caption("الصيغ المسموحة: PDF / DOCX / XLSX (حتى 200MB لكل ملف).")

files = st.file_uploader(
    "أرفقي الملفات",
    type=["pdf", "docx", "xlsx"],
    accept_multiple_files=True
)

run = st.button("ابدأ الفرز الآن", type="primary")

st.divider()
st.subheader("النتائج")

# ===== توابع مساعدة =====
AR_DIACS = "".join([
    "\u064B", "\u064C", "\u064D", "\u064E", "\u064F", "\u0650", "\u0651", "\u0652", "\u0670", "\u0653"
])

def normalize_ar(s: str) -> str:
    if not s:
        return ""
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    s = s.replace("ى", "ي").replace("ئ", "ي").replace("ؤ", "و")
    s = s.replace("ـ", "")  # تطويل
    for d in AR_DIACS:
        s = s.replace(d, "")
    return s.lower().strip()

def read_pdf(file) -> str:
    from PyPDF2 import PdfReader
    text_parts = []
    try:
        reader = PdfReader(file)
        for p in reader.pages:
            try:
                text_parts.append(p.extract_text() or "")
            except Exception:
                pass
    except Exception:
        # في بعض المنصات نحتاج إعادة البافر
        data = file.read()
        bio = io.BytesIO(data)
        reader = PdfReader(bio)
        for p in reader.pages:
            text_parts.append(p.extract_text() or "")
    return "\n".join(text_parts)

def read_docx(file) -> str:
    import docx2txt
    data = file.read()
    bio = io.BytesIO(data)
    return docx2txt.process(bio) or ""

def read_xlsx(file) -> str:
    import pandas as pd
    text_parts = []
    try:
        xls = pd.ExcelFile(file)
    except Exception:
        # أحيانًا يحتاج BytesIO
        data = file.read()
        xls = pd.ExcelFile(io.BytesIO(data))
    for name in xls.sheet_names:
        try:
            df = xls.parse(name)
            text_parts.append(name)
            text_parts.append(df.head(50).to_string(index=False))
        except Exception:
            pass
    return "\n".join(text_parts)

def fuzzy_all_present(haystack: str, needles: list[str], threshold: int = 80) -> bool:
    """
    يعتبر الشرط محقّقًا إذا كانت أي صياغة من العبارة موجودة بتشابه >= threshold.
    نستخدم token_set_ratio لأنها أمتن مع اختلاف الترتيب.
    """
    H = normalize_ar(haystack)
    for raw in needles:
        q = normalize_ar(raw)
        if not q:  # حقل فارغ -> نتجاهله
            continue
        score = fuzz.token_set_ratio(q, H)
        if score < threshold:
            return False
    return True

# ===== التنفيذ =====
if run:
    if not files:
        st.warning("رجاءً أرفقي ملفًا واحدًا على الأقل.")
    else:
        needles = [uni, major, nation]
        ok = 0
        for file in files:
            name = file.name
            ext = name.split(".")[-1].lower()

            # قراءة المحتوى
            try:
                if ext == "pdf":
                    content = read_pdf(file)
                elif ext == "docx":
                    content = read_docx(file)
                elif ext == "xlsx":
                    content = read_xlsx(file)
                else:
                    st.error(f"⚠️ صيغة غير مدعومة: {ext}")
                    continue
            except Exception as e:
                st.error(f"تعذّرت قراءة {name} — {e}")
                continue

            # المطابقة
            try:
                is_match = fuzzy_all_present(content, needles, THRESH)
            except Exception as e:
                st.error(f"تعذّرت مطابقة {name} — {e}")
                continue

            if is_match:
                st.success(f"✅ {name} — مطابق للشروط (عتبة {THRESH}%)")
                ok += 1
            else:
                st.error(f"❌ {name} — غير مطابق (أقل من {THRESH}%)")

        st.info(f"انتهى الفرز. الملفات المطابقة: {ok}")