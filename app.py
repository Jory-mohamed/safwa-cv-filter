# app.py
import streamlit as st
from pathlib import Path

# تحديد مسار اللوقو داخل مجلد static
logo_path = Path("static/logo.png")

# عرض اللوقو في أعلى الصفحة
st.image(str(logo_path), width=120)  # تقدرِ تتحكمي بالحجم من widthimport streamlit as st
from io import BytesIO
from pathlib import Path
from typing import List

# قراءة الصيغ
from PyPDF2 import PdfReader
import docx2txt
import pandas as pd

# Fuzzy matching
from rapidfuzz import fuzz

# ---------------- Config & CSS ----------------
st.set_page_config(
    page_title="صفوة | فرز السير الذاتية",
    page_icon="static/logo.png",
    layout="centered"
)

# تحميل CSS
css_path = Path("static/style.css")
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# هيدر + لوقو
logo_exists = Path("static/logo.png").exists()
st.markdown(
    f"""
    <div class="brand">
        {'<img src="static/logo.png" alt="Safwa Logo"/>' if logo_exists else ''}
        <div class="title">
            <h1>صفوة</h1>
            <small>تميّز بخطوة</small>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("### فرز السير الذاتية")

# ---------------- Helpers ----------------
AR_DIACS = "".join([
    "\u064b", "\u064c", "\u064d", "\u064e", "\u064f", "\u0650", "\u0651", "\u0652", "\u0670"
])

def normalize_ar(s: str) -> str:
    if not s:
        return ""
    # إزالة التشكيل
    for d in AR_DIACS:
        s = s.replace(d, "")
    # توحيد الألفات و الهاء/ة والياء
    repl = {
        "أ":"ا", "إ":"ا", "آ":"ا",
        "ة":"ه",
        "ى":"ي",
        "ؤ":"و", "ئ":"ي",
        "ٔ":"", "ٰ":""
    }
    for k,v in repl.items():
        s = s.replace(k, v)
    return s

def text_from_pdf(file: BytesIO) -> str:
    out = []
    reader = PdfReader(file)
    for p in reader.pages:
        try:
            t = p.extract_text() or ""
        except Exception:
            t = ""
        out.append(t)
    return "\n".join(out)

def text_from_docx(file: BytesIO) -> str:
    # docx2txt يحتاج مسار: نكتب الملف مؤقتاً
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=True) as tmp:
        tmp.write(file.read())
        tmp.flush()
        return docx2txt.process(tmp.name) or ""

def text_from_xlsx(file: BytesIO) -> str:
    out = []
    try:
        xls = pd.ExcelFile(file)
        for sh in xls.sheet_names:
            df = xls.parse(sh, dtype=str).fillna("")
            out.append("\n".join([" ".join(row) for row in df.values]))
    except Exception:
        # محاولة مباشرة
        try:
            df = pd.read_excel(file, dtype=str).fillna("")
            out.append("\n".join([" ".join(row) for row in df.values]))
        except Exception:
            pass
    return "\n".join(out)

def fuzzy_found(needle: str, haystack: str, thresh: int = 80) -> bool:
    if not needle.strip():
        return True
    a = normalize_ar(needle).lower()
    b = normalize_ar(haystack).lower()
    # استخدم token_set_ratio عشان اختلاف الترتيب
    score = fuzz.token_set_ratio(a, b)
    return score >= thresh

def nationality_keywords(value: str) -> List[str]:
    v = normalize_ar(value).lower().strip()
    if not v:
        return []
    saudi = [
        "سعودي", "سعوديه", "سعوديه", "مواطن سعودي",
        "saudi", "saudi arabia", "ksa", "saudi national"
    ]
    non_saudi = [
        "غير سعودي", "غير سعوديه", "غيرسعودي",
        "non-saudi", "non saudi", "expat", "غير سعودي الجنسية"
    ]
    if "غير" in v or "non" in v:
        return non_saudi
    else:
        return saudi

def read_any(file) -> str:
    name = file.name.lower()
    data = file.read()
    buf = BytesIO(data)
    if name.endswith(".pdf"):
        return text_from_pdf(buf)
    elif name.endswith(".docx"):
        return text_from_docx(BytesIO(data))  # مرر نسخة جديدة
    elif name.endswith(".xlsx"):
        return text_from_xlsx(BytesIO(data))
    return ""

# ---------------- UI ----------------
with st.container():
    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    uni   = c1.text_input("الجامعة", placeholder="مثال: جامعة الملك سعود")
    major = c2.text_input("التخصص", placeholder="مثال: نظم معلومات إدارية")
    nation = st.text_input("الجنسية", placeholder="مثال: سعودي / غير سعودي / Saudi / Non-Saudi")

    files = st.file_uploader(
        "إرفاق ملفات CV (PDF / DOCX / XLSX)",
        type=["pdf","docx","xlsx"],
        accept_multiple_files=True
    )
    run = st.button("ابدأ الفرز الآن", type="primary")
    st.markdown('</div>', unsafe_allow_html=True)

# ثابت ومخفي: حد المطابقة 80
THRESH = 80

# ---------------- Logic ----------------
if run:
    if not files:
        st.warning("فضلاً أرفقي ملفاً واحداً على الأقل.")
    else:
        with st.status("جارٍ قراءة الملفات…", expanded=False):
            results = []
            for f in files:
                try:
                    content = read_any(f)
                except Exception:
                    content = ""
                ok_uni   = fuzzy_found(uni, content, THRESH) if uni.strip() else True
                ok_major = fuzzy_found(major, content, THRESH) if major.strip() else True

                ok_nation = True
                if nation.strip():
                    nkeys = nationality_keywords(nation)
                    if nkeys:
                        ok_nation = any(fuzzy_found(k, content, THRESH) for k in nkeys)

                passed = (ok_uni and ok_major and ok_nation)
                results.append((f.name, passed, ok_uni, ok_major, ok_nation))

        st.markdown("### النتائج")
        any_pass = False
        for name, passed, ou, om, on in results:
            if passed:
                any_pass = True
                st.success(f"✅ مطابق للشروط: **{name}**")
            else:
                msgs = []
                if not ou: msgs.append("الجامعة")
                if not om: msgs.append("التخصص")
                if not on: msgs.append("الجنسية")
                detail = "، ".join(msgs) if msgs else "غير محدد"
                st.error(f"❌ غير مطابق: **{name}** — لم تتحقق: {detail}")

        if not any_pass:
            st.info("لا توجد نتائج مطابقة بناءً على المعايير المدخلة.")

# تذييل صغير
st.markdown(
    "<div style='text-align:center;color:#9aa3b2;margin-top:18px'>© صفوة — تميّز بخطوة</div>",
    unsafe_allow_html=True
)