import streamlit as st
import re, unicodedata, io
from pypdf import PdfReader

# ====== إعداد الصفحة + علامة الإصدار ======
st.set_page_config(page_title="فلترة السير الذاتية", page_icon="🗂️", layout="centered")
st.title("🗂️ برنامج فلترة السير الذاتية")
st.caption("Version: 1.3  •  يطابق: الجامعة + التخصص + الجنسية  •  يدعم رفع عدة ملفات PDF")

# ====== دوال مساعدة ======
def normalize_ar(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = ''.join(ch for ch in unicodedata.normalize('NFKD', text) if not unicodedata.combining(ch))
    text = re.sub(r"[أإآٱ]", "ا", text)
    text = text.replace("ة","ه").replace("ى","ي")
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

def check_requirement(req_value, text):
    """يرجع: (True/False/None, [hits])"""
    if not req_value.strip():
        return None, []
    norm = normalize_ar(text)
    norm_req = normalize_ar(req_value)
    return (norm_req in norm), ([req_value] if norm_req in norm else [])

def evaluate_cv(raw_text, uni_req, major_req, nat_req):
    uni_ok, uni_hits     = check_requirement(uni_req,   raw_text)
    major_ok, major_hits = check_requirement(major_req, raw_text)
    nat_ok, nat_hits     = check_requirement(nat_req,   raw_text)

    all_ok = (uni_ok is not None and major_ok is not None and nat_ok is not None) and (uni_ok and major_ok and nat_ok)
    verdict = "✅ مطابق للشروط" if all_ok else "❌ غير مطابق"
    detail = [
        ("الجامعة", uni_ok, uni_hits),
        ("التخصص", major_ok, major_hits),
        ("الجنسية", nat_ok,  nat_hits),
    ]
    return verdict, detail

def render_detail(detail):
    for label, ok, hits in detail:
        if ok is None:
            st.write(f"**{label}:** ⏭️ لم يتم تحديد شرط")
        else:
            st.write(f"**{label}:** {'✅ موجود' if ok else '❌ غير موجود'}")
            if hits:
                st.caption("المطابقات: " + ", ".join(hits))

# ====== خانات المتطلبات ======
st.subheader("✨ حددي المتطلبات")
col1, col2, col3 = st.columns(3)
with col1:
    uni_req = st.text_input("🏫 الجامعة المطلوبة", placeholder="مثال: جامعة الملك سعود / KSU")
with col2:
    major_req = st.text_input("📚 التخصص المطلوب", placeholder="مثال: نظم المعلومات الإدارية / MIS")
with col3:
    nat_req = st.text_input("🌍 الجنسية المطلوبة", placeholder="مثال: سعودي / سعودية / Saudi")

st.divider()

# ====== رفع عدة ملفات ======
st.subheader("📂 ارفعي جميع ملفات الـ CV دفعة واحدة")
files = st.file_uploader("ملفات PDF", type=["pdf"], accept_multiple_files=True)

if st.button("تحقّق من الملفات", type="primary"):
    if not files:
        st.warning("فضلاً ارفعي ملفًا واحدًا على الأقل.")
    else:
        for i, f in enumerate(files, start=1):
            st.divider()
            st.write(f"**📄 الملف {i}:** `{f.name}`")
            try:
                raw = extract_pdf_text(f.read())
            except Exception as e:
                st.error(f"تعذّر قراءة `{f.name}`: {e}")
                continue

            verdict, detail = evaluate_cv(raw, uni_req, major_req, nat_req)
            st.markdown(f"**النتيجة:** {verdict}")
            render_detail(detail)

st.caption("🔎 ملاحظة: لو كان الـ PDF صورة ممسوحة، نضيف OCR لاحقاً. النسخة الحالية بلا OCR لتسهيل النشر.")
