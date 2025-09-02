import streamlit as st
import re
import unicodedata
from pypdf import PdfReader
import io

# إعداد الصفحة
st.set_page_config(page_title="فرز السير الذاتية - HR Filter", page_icon="🗂️", layout="centered")
st.title("🗂️ برنامج فرز السير الذاتية")
st.caption("يتحقق من: **جامعة الملك سعود** + **نظم المعلومات الإدارية** + **الجنسية السعودية**")

# --------- دوال مساعدة ---------
def normalize_ar(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = ''.join(ch for ch in unicodedata.normalize('NFKD', text) if not unicodedata.combining(ch))
    text = re.sub(r"[أإآٱ]", "ا", text)
    text = text.replace("ة", "ه").replace("ى", "ي")
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

# --------- القواعد ---------
UNI_PATTERNS = [
    r"\bجامعه?\s+الملك\s+سعود\b",
    r"\bking\s+saud\s+university\b",
    r"\bksu\b"
]
MAJOR_PATTERNS = [
    r"\bنظم\s+المعلومات\s+الاداري(?:ه|ة)?\b",
    r"\bاداره?\s+نظم\s+معلومات\b",
    r"\bmis\b",
    r"\bmanagement\s+information\s+systems?\b"
]
NAT_PATTERNS = [
    r"\bسعودي(?:ه)?\b",
    r"\bsaudi(?:\s+(?:arabia|national))?\b"
]

def find_matches(patterns, text):
    hits = []
    for p in patterns:
        for m in re.findall(p, text, flags=re.IGNORECASE):
            if isinstance(m, tuple):
                m = " ".join([x for x in m if isinstance(x, str)])
            hits.append(m if isinstance(m, str) else "")
    hits = [h.strip() for h in hits if h and h.strip()]
    return (len(hits) > 0), hits

def evaluate_cv(raw_text: str):
    norm = normalize_ar(raw_text)
    uni_ok, uni_hits = find_matches(UNI_PATTERNS, norm)
    major_ok, major_hits = find_matches(MAJOR_PATTERNS, norm)
    nat_ok, nat_hits = find_matches(NAT_PATTERNS, norm)

    all_ok = uni_ok and major_ok and nat_ok
    verdict = "✅ مطابق للشروط" if all_ok else "❌ غير مطابق"

    detail = [
        ("الجامعة", uni_ok, uni_hits),
        ("التخصص", major_ok, major_hits),
        ("الجنسية", nat_ok, nat_hits),
    ]
    return verdict, detail

def render_detail(detail):
    for label, ok, hits in detail:
        st.write(f"**{label}:** {'✅ موجود' if ok else '❌ غير موجود'}")
        if hits:
            with st.expander(f"الألفاظ التي تم العثور عليها في {label}"):
                for h in sorted(set(hits)):
                    st.code(h, language="text")

# --------- الواجهة (خانة وحدة) ---------
st.subheader("✨ ارفعي جميع ملفات الـ CV دفعة واحدة")
files = st.file_uploader("ارفعي ملفات PDF", type=["pdf"], accept_multiple_files=True)

if st.button("تحقّق من الملفات", type="primary"):
    if not files:
        st.warning("فضلاً ارفعي ملفًا واحدًا على الأقل.")
    else:
        for idx, f in enumerate(files, start=1):
            st.divider()
            st.write(f"**📄 الملف {idx}:** `{f.name}`")
            try:
                raw = extract_pdf_text(f.read())
            except Exception as e:
                st.error(f"تعذّر قراءة `{f.name}`: {e}")
                continue

            verdict, detail = evaluate_cv(raw)
            st.markdown(f"**النتيجة:** {verdict}")
            render_detail(detail)

st.caption("🔎 ملاحظة: إذا كان ملف الـ PDF صورة ممسوحة، ما راح ينقرأ نصه إلا بإضافة OCR مستقبلاً.")
