# app.py
import streamlit as st
from io import BytesIO
import pdfplumber
from rapidfuzz import fuzz

# ---------------- Page ----------------
st.set_page_config(page_title="صفوة • فرز السير الذاتية", layout="centered")

# ---------------- Helpers ----------------
AR_DIACRITICS = "".join([
    "\u0610","\u0611","\u0612","\u0613","\u0614","\u0615","\u0616","\u0617","\u0618","\u0619","\u061A",
    "\u064B","\u064C","\u064D","\u064E","\u064F","\u0650","\u0651","\u0652","\u0653","\u0654","\u0655",
    "\u0656","\u0657","\u0658","\u0659","\u065A","\u065B","\u065C","\u065D","\u065E","\u065F",
    "\u0670","\u06D6","\u06D7","\u06D8","\u06D9","\u06DA","\u06DB","\u06DC","\u06DF","\u06E0",
    "\u06E1","\u06E2","\u06E3","\u06E4","\u06E7","\u06E8","\u06EA","\u06EB","\u06EC","\u06ED"
])

def normalize_ar(s: str) -> str:
    if not s:
        return ""
    s = s.strip()
    # remove diacritics & tatweel
    for ch in AR_DIACRITICS:
        s = s.replace(ch, "")
    s = s.replace("ـ","")
    # unify alef/hamza forms
    s = (s.replace("أ","ا")
           .replace("إ","ا")
           .replace("آ","ا")
           .replace("ٱ","ا")
           .replace("ؤ","و")
           .replace("ئ","ي"))
    # taa marbuta / alif maqsura
    s = s.replace("ى","ي").replace("ة","ه")
    # numbers/latin spacing normalizer
    return " ".join(s.split()).lower()

def read_pdf_text(file_bytes: bytes) -> str:
    txt_parts = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if t:
                txt_parts.append(t)
    return "\n".join(txt_parts)

def fuzzy_contains(needle: str, haystack: str, threshold: int = 80) -> bool:
    n = normalize_ar(needle)
    h = normalize_ar(haystack)
    if not n or not h:
        return False
    return fuzz.partial_ratio(n, h) >= threshold

# ---------------- UI ----------------
st.markdown(
    """
    <div style="text-align:center;margin:12px 0 6px 0;">
      <img src="static/logo.png" alt="Safwa" height="64">
      <h1 style="margin:8px 0 0 0;">صفوة</h1>
      <div style="color:#0A1A2F;opacity:0.8;">تميّز بخطوة</div>
    </div>
    """,
    unsafe_allow_html=True
)

col1, col2 = st.columns(2)
with col1:
    uni = st.text_input("الجامعة", placeholder="مثال: جامعة الملك سعود")
with col2:
    major = st.text_input("التخصص", placeholder="مثال: نظم المعلومات الإدارية")

nation = st.text_input("الجنسية", placeholder="مثال: سعودي / غير سعودي")
# الإضافي مخفي/ملغي حسب رغبتك – إن أردته لاحقاً أعيده
# extra = st.text_input("كلمات اختيارية (اختياري)")

uploaded = st.file_uploader("أرفق ملفات CV (PDF فقط الآن)", type=["pdf"], accept_multiple_files=True)

# نسبة المطابقة ثابتة 80 (مخفية كما طلبت)
THRESH = 80

if st.button("ابدأ الفرز"):
    if not uploaded:
        st.warning("فضلاً ارفع ملفاً واحداً على الأقل.")
    else:
        for file in uploaded:
            try:
                raw = file.read()
                content = read_pdf_text(raw)

                # Debug لمساعدتك: إظهار مقتطف صغير من النص المستخرج (اختياري)
                with st.expander(f"نص مستخرج من {file.name}"):
                    preview = (content or "")[:1000]
                    st.code(preview if preview else "لم يُستخرج نص (قد يكون الملف صورة ممسوحة).", language="text")

                conditions = [
                    fuzzy_contains(uni, content) if uni.strip() else True,
                    fuzzy_contains(major, content) if major.strip() else True,
                    fuzzy_contains(nation, content) if nation.strip() else True,
                    # fuzzy_contains(extra, content) if extra.strip() else True,  # لو رجعناه
                ]

                if all(conditions):
                    st.success(f"✅ مطابق — {file.name}")
                else:
                    st.error(f"❌ غير مطابق — {file.name}")

            except Exception as e:
                st.error(f"تعذّر قراءة {file.name}: {e}")