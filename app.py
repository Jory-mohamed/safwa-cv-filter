import streamlit as st
import re, unicodedata, io
from pypdf import PdfReader
from rapidfuzz import fuzz

# ===== إعداد الصفحة =====
st.set_page_config(page_title="فلترة السير الذاتية", page_icon="🗂️", layout="centered")
st.title("🗂️ فلترة السير الذاتية")
st.caption("Version: 2.0 • يدعم الرفع المتعدد + المطابقة الذكية (Fuzzy) + المرادفات والعتبة")

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

# ===== المطابقة =====
def exact_contains(term: str, text: str) -> (bool, int):
    """مطابقة حرفية بعد التطبيع"""
    if not term.strip():
        return None, 0
    norm_text = normalize_ar(text)
    norm_term = normalize_ar(term)
    found = norm_term in norm_text
    return found, 100 if found else 0

def fuzzy_contains(term: str, text: str, threshold: int = 85) -> (bool, int):
    """مطابقة ذكية: نحسب أعلى درجة بين partial_ratio و token_set_ratio"""
    if not term.strip():
        return None, 0
    norm_text = normalize_ar(text)
    norm_term = normalize_ar(term)
    score1 = fuzz.partial_ratio(norm_term, norm_text)
    score2 = fuzz.token_set_ratio(norm_term, norm_text)
    score = max(score1, score2)
    return (score >= threshold), int(score)

def check_with_synonyms(text: str, base_value: str, synonyms: list, use_fuzzy: bool, threshold: int):
    """
    يرجع (ok, best_score, hits)
    - ok: True/False/None
    - best_score: أعلى درجة وصلنا لها
    - hits: قائمة بالكلمات/المرادفات التي طابقت
    """
    if not base_value.strip() and not any(s.strip() for s in synonyms):
        return None, 0, []
    terms = [t for t in [base_value.strip(), *[s.strip() for s in synonyms]] if t]
    best = 0
    hits = []
    # جرّب كل مصطلح
    for t in terms:
        ok, score = (fuzzy_contains(t, text, threshold) if use_fuzzy else exact_contains(t, text))
        if ok:
            hits.append(f"{t} (score={score})")
            best = max(best, score)
    ok_final = True if hits else False
    return ok_final, best, hits

# ===== واجهة إدخال الشروط =====
st.subheader("✨ حددي المتطلبات")
col1, col2, col3 = st.columns(3)
with col1:
    uni_req = st.text_input("🏫 الجامعة المطلوبة", placeholder="مثال: جامعة الملك سعود / KSU")
    uni_syn = st.text_input("مرادفات الجامعة (اختياري، افصلي بفواصل)", placeholder="KSU, King Saud University")
with col2:
    major_req = st.text_input("📚 التخصص المطلوب", placeholder="مثال: نظم المعلومات الإدارية / MIS")
    major_syn = st.text_input("مرادفات التخصص (اختياري)", placeholder="ادارة نظم معلومات, MIS, Management Information Systems")
with col3:
    nat_req = st.text_input("🌍 الجنسية المطلوبة", placeholder="مثال: سعودي / سعودية / Saudi")
    nat_syn = st.text_input("مرادفات الجنسية (اختياري)", placeholder="saudi national")

st.divider()

# إعدادات المطابقة
st.subheader("⚙️ إعدادات الدقة")
c1, c2 = st.columns([1,2])
with c1:
    use_fuzzy = st.checkbox("تفعيل المطابقة الذكية (Fuzzy)", value=True)
with c2:
    threshold = st.slider("عتبة التطابق (كلما زادت صار التشدد أعلى)", min_value=60, max_value=95, value=85, step=1)

# ===== رفع ملفات =====
st.subheader("📂 ارفعي جميع ملفات الـ CV دفعة واحدة")
files = st.file_uploader("ملفات PDF", type=["pdf"], accept_multiple_files=True)

def evaluate_cv(text_raw: str):
    uni_ok, uni_score, uni_hits     = check_with_synonyms(text_raw, uni_req,  uni_syn.split(",") if uni_syn else [],  use_fuzzy, threshold)
    major_ok, major_score, major_hits = check_with_synonyms(text_raw, major_req, major_syn.split(",") if major_syn else [], use_fuzzy, threshold)
    nat_ok, nat_score, nat_hits     = check_with_synonyms(text_raw, nat_req,  nat_syn.split(",") if nat_syn else [],  use_fuzzy, threshold)

    # الحكم النهائي: كل الشروط المحددة يجب أن تكون True؛ الشروط الفارغة تُهمل (None)
    req_flags = [x for x in [uni_ok, major_ok, nat_ok] if x is not None]
    all_ok = (len(req_flags) > 0) and all(req_flags)
    verdict = "✅ مطابق للشروط" if all_ok else "❌ غير مطابق"

    detail = [
        ("الجامعة", uni_ok, uni_score, uni_hits),
        ("التخصص", major_ok, major_score, major_hits),
        ("الجنسية", nat_ok, nat_score, nat_hits),
    ]
    return verdict, detail

def render_detail(detail):
    for label, ok, score, hits in detail:
        if ok is None:
            st.write(f"**{label}:** ⏭️ لم يتم تحديد شرط")
        else:
            icon = "✅" if ok else "❌"
            st.write(f"**{label}:** {icon} — (score={score})")
            if hits:
                with st.expander(f"المطابقات المكتشفة في {label}"):
                    for h in sorted(set(hits)):
                        st.code(h, language="text")

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

st.caption("🔎 ملاحظات: 1) إذا كان الـ PDF صورة ممسوحة، نضيف OCR لاحقاً. 2) جرّبي threshold = 80–88 عادةً مناسبة. 3) أضيفي مرادفات لزيادة الدقة.")
