import streamlit as st
import re
import unicodedata
from pypdf import PdfReader
import io

# ========= إعداد الصفحة =========
st.set_page_config(page_title="فرز السير الذاتية - HR Filter", page_icon="🗂️", layout="centered")
st.title("🗂️ برنامج فرز السير الذاتية (نسخة تجريبية)")
st.caption("يتحقق من: **جامعة الملك سعود** + **نظم المعلومات الإدارية** + **الجنسية السعودية**")

# ========= أدوات مساعدة =========
def normalize_ar(text: str) -> str:
    """تطبيع بسيط للنص العربي/الإنجليزي لتقليل أخطاء المطابقة."""
    if not text:
        return ""
    text = text.lower()
    # إزالة التشكيل
    text = ''.join(ch for ch in unicodedata.normalize('NFKD', text) if not unicodedata.combining(ch))
    # توحيد بعض الحروف
    text = re.sub(r"[أإآٱ]", "ا", text)
    text = text.replace("ة", "ه").replace("ى", "ي")
    # مسافات وعلامات زائدة
    text = re.sub(r"[^0-9a-z\u0600-\u06FF\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_pdf_text(file_bytes: bytes) -> str:
    """قراءة نص الـ PDF (بدون OCR)."""
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for p in reader.pages:
        try:
            pages.append(p.extract_text() or "")
        except Exception:
            pages.append("")
    return "\n".join(pages)

# ========= أنماط البحث (قواعد) =========
# جامعة الملك سعود
UNI_PATTERNS = [
    r"\bجامعه?\s+الملك\s+سعود\b",
    r"\bking\s+saud\s+university\b",
    r"\bksu\b"
]

# نظم المعلومات الإدارية (مرادفات شائعة)
MAJOR_PATTERNS = [
    r"\bنظم\s+المعلومات\s+الاداري(?:ه|ة)?\b",
    r"\bاداره?\s+نظم\s+معلومات\b",
    r"\bmis\b",
    r"\bmanagement\s+information\s+systems?\b"
]

# الجنسية السعودية
NAT_PATTERNS = [
    r"\bسعودي(?:ه)?\b",
    r"\bsaudi(?:\s+(?:arabia|national))?\b"
]

def find_matches(patterns, text):
    """يرجع: موجود/غير موجود + قائمة بالألفاظ التي وُجدت فعلاً."""
    hits = []
    for p in patterns:
        for m in re.findall(p, text, flags=re.IGNORECASE):
            if isinstance(m, tuple):
                # لو الرجكس فيه مجموعات، نحولها لنص واحد
                m = " ".join([x for x in m if isinstance(x, str)])
            hits.append(m if isinstance(m, str) else "")
    # تنظيف النتائج
    hits = [h.strip() for h in hits if h and h.strip()]
    return (len(hits) > 0), hits

def evaluate_cv(raw_text: str):
    """يرجع النتيجة النهائية + تفصيل الشروط + الألفاظ المطابقة."""
    norm = normalize_ar(raw_text)
    uni_ok, uni_hits   = find_matches(UNI_PATTERNS,   norm)
    major_ok, major_hits = find_matches(MAJOR_PATTERNS, norm)
    nat_ok, nat_hits   = find_matches(NAT_PATTERNS,   norm)

    all_ok = uni_ok and major_ok and nat_ok
    verdict = "✅ مطابق للشروط" if all_ok else "❌ غير مطابق"

    detail = [
        ("الجامعة", uni_ok, uni_hits),
        ("التخصص", major_ok, major_hits),
        ("الجنسية", nat_ok, nat_hits),
    ]
    return verdict, detail, norm

def render_detail(detail):
    """يعرض تفصيل الشروط + الألفاظ المطابقة بشكل واضح."""
    for label, ok, hits in detail:
        st.write(f"**{label}:** {'✅ موجود' if ok else '❌ غير موجود'}")
        if hits:
            with st.expander(f"الألفاظ التي تم العثور عليها في {label}"):
                for h in sorted(set(hits)):
                    st.code(h, language="text")

# ========= الواجهة =========
tab_single, tab_multi, tab_samples = st.tabs(["تحقق من سيرة واحدة", "تحقق من عدة ملفات", "أمثلة جاهزة"])

# --- تبويب: سيرة واحدة ---
with tab_single:
    st.subheader("أدخلي نص السيرة أو ارفعي PDF")
    col1, col2 = st.columns(2)
    with col1:
        cv_text = st.text_area("نص السيرة الذاتية (اختياري إذا سترفعين PDF)", height=220, placeholder="الاسم ... الجامعة ... التخصص ... الجنسية ...")
    with col2:
        one_file = st.file_uploader("أو ارفعي ملف PDF واحد", type=["pdf"], accept_multiple_files=False)

    if st.button("تحقّق الآن", type="primary"):
        if one_file and not cv_text.strip():
            try:
                raw = extract_pdf_text(one_file.read())
            except Exception as e:
                st.error(f"تعذّر قراءة الـ PDF: {e}")
                raw = ""
        else:
            raw = cv_text

        if not raw.strip():
            st.warning("فضلاً أدخلي نصًا أو ارفعي ملف PDF.")
        else:
            verdict, detail, norm = evaluate_cv(raw)
            st.markdown(f"### النتيجة النهائية: {verdict}")
            render_detail(detail)
            with st.expander("عرض النص الذي تم تحليله"):
                st.text(raw)

# --- تبويب: عدة ملفات ---
with tab_multi:
    st.subheader("ارفعي عدة ملفات PDF وسيتم التحقق من كل ملف")
    files = st.file_uploader("ارفعي ملفات PDF", type=["pdf"], accept_multiple_files=True)

    if st.button("تحقّق من جميع الملفات", type="secondary"):
        if not files:
            st.warning("فضلاً ارفعي ملفًا واحدًا على الأقل.")
        else:
            for idx, f in enumerate(files, start=1):
                st.divider()
                st.write(f"**الملف {idx}:** `{f.name}`")
                try:
                    raw = extract_pdf_text(f.read())
                except Exception as e:
                    st.error(f"تعذّر قراءة `{f.name}`: {e}")
                    continue

                verdict, detail, norm = evaluate_cv(raw)
                st.markdown(f"**النتيجة:** {verdict}")
                render_detail(detail)

# --- تبويب: أمثلة جاهزة ---
with tab_samples:
    st.subheader("تجربة بعينات نصية")
    samples = [
        ("عينة 1 (يجب أن تكون ✅)", "الجامعه: جامعة الملك سعود\nالتخصص: نظم المعلومات الاداريه\nالجنسيه: سعوديه"),
        ("عينة 2 (يجب أن تكون ✅)", "University: King Saud University\nMajor: MIS\nNationality: Saudi"),
        ("عينة 3 (يجب أن تكون ❌)", "الجامعة: جامعة الملك خالد\nالتخصص: محاسبة\nالجنسية: غير سعودي"),
    ]
    for title, s in samples:
        st.write(f"**{title}**")
        st.code(s, language="text")
        v, d, _ = evaluate_cv(s)
        st.write(f"النتيجة: {v}")
        render_detail(d)
        st.divider()

st.caption("🔎 ملاحظة: إذا كان الـ PDF عبارة عن صورة ممسوحة (بدون نص)، قد تحتاجين لاحقًا لإضافة OCR. النسخة الحالية لا تستخدم OCR عمدًا لتسهيل النشر.")
