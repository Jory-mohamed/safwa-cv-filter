import streamlit as st
import re, unicodedata, io
from pypdf import PdfReader
from rapidfuzz import fuzz

# ===== إعداد الصفحة =====
st.set_page_config(page_title="فلترة السير الذاتية", page_icon="🗂️", layout="centered")
st.title("🗂️ فلترة السير الذاتية")
st.caption("Version: 2.2 • مطابقة مركّبة للتخصص + مرونة بالجامعة والجنسية")

# ===== أدوات مساعدة =====
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

def fuzzy_match(term: str, text: str, threshold: int = 80) -> (bool, int):
    if not term.strip():
        return None, 0
    norm_text = normalize_ar(text)
    norm_term = normalize_ar(term)
    score1 = fuzz.partial_ratio(norm_term, norm_text)
    score2 = fuzz.token_set_ratio(norm_term, norm_text)
    score = max(score1, score2)
    return (score >= threshold), int(score)

# ===== واجهة إدخال المتطلبات =====
st.subheader("✨ حددي المتطلبات")

col1, col2, col3 = st.columns(3)
with col1:
    uni_req = st.text_input("🏫 الجامعة المطلوبة", placeholder="مثال: جامعة الملك سعود / KSU")
with col2:
    major_req = st.text_input("📚 التخصص المطلوب", placeholder="مثال: نظم المعلومات الإدارية / MIS")
    major_syn = st.text_input("مرادفات التخصص (اختياري)", placeholder="إدارة نظم معلومات, MIS, Management Information Systems")
with col3:
    nat_req = st.text_input("🌍 الجنسية المطلوبة", placeholder="مثال: سعودي / سعودية / Saudi")

st.divider()

# ===== رفع الملفات =====
st.subheader("📂 ارفعي ملفات الـ CV دفعة واحدة")
files = st.file_uploader("ملفات PDF", type=["pdf"], accept_multiple_files=True)

# ===== التحقق =====
def evaluate_cv(text_raw: str, threshold: int = 80):
    norm_text = normalize_ar(text_raw)

    # الجامعة والجنسية بالمطابقة الذكية العادية
    uni_ok, uni_score = fuzzy_match(uni_req, norm_text, threshold)
    nat_ok, nat_score = fuzzy_match(nat_req, norm_text, threshold)

    # التخصص: مطابقة مركبة (لازم كلمتين أو أكثر)
    major_ok, major_score = fuzzy_match(major_req, norm_text, threshold)
    syn_hits = []

    # لو حاطّة مرادفات
    if major_syn.strip():
        for s in major_syn.split(","):
            ok, score = fuzzy_match(s.strip(), norm_text, threshold)
            if ok:
                major_ok = True
                major_score = max(major_score, score)
                syn_hits.append(f"{s.strip()} (score={score})")

    # فحص الكلمات الأساسية (مثلاً: نظم + معلومات + اداريه/إدارية)
    base_keywords = ["نظم", "معلومات"]
    kw_hits = [kw for kw in base_keywords if kw in norm_text]
    if len(kw_hits) >= 2:  # لقى على الأقل كلمتين
        major_ok = True
        major_score = max(major_score, 90)
        syn_hits.append(" ".join(kw_hits) + " (تركيبي)")

    # الحكم النهائي
    req_flags = [x for x in [uni_ok, major_ok, nat_ok] if x is not None]
    all_ok = (len(req_flags) > 0) and all(req_flags)
    verdict = "✅ مطابق للشروط" if all_ok else "❌ غير مطابق"

    detail = [
        ("الجامعة", uni_ok, uni_score, []),
        ("التخصص", major_ok, major_score, syn_hits),
        ("الجنسية", nat_ok, nat_score, []),
    ]
    return verdict, detail

def render_detail(detail):
    for label, ok, score, hits in detail:
        if ok is None:
            st.write(f"**{label}:** ⏭️ لم يتم تحديد شرط")
        else:
            icon = "✅" if ok else "❌"
            st.write(f"**{label}:** {icon} (score={score})")
            if hits:
                st.caption("مطابقات: " + ", ".join(hits))

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

            verdict, detail = evaluate_cv(raw)
            st.markdown(f"**النتيجة:** {verdict}")
            render_detail(detail)

st.caption("🔎 ملاحظة: التخصص يتطلب مطابقة مرنة + كلمات أساسية معًا (نظم + معلومات). PDF مصور يحتاج OCR لاحقًا.")
