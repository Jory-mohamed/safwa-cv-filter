import streamlit as st
from io import BytesIO
import pdfplumber
from rapidfuzz import fuzz

# -------- إعداد الصفحة --------
st.set_page_config(page_title="صفوة • فرز السير الذاتية", layout="centered")
st.title("صفوة لفرز السير الذاتية")
st.caption("تميّز بخطوة — نسخة تشخيصية (تبيّن الدرجات لكل شرط)")

# -------- أدوات مساعدة --------
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
    for ch in AR_DIACRITICS: s = s.replace(ch, "")
    s = s.replace("ـ","")  # تطويل
    s = (s.replace("أ","ا").replace("إ","ا").replace("آ","ا").replace("ٱ","ا")
           .replace("ؤ","و").replace("ئ","ي").replace("ى","ي").replace("ة","ه"))
    s = " ".join(s.split()).lower()
    return s

def read_pdf_text(file_bytes: bytes) -> str:
    txt = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            txt.append(t)
    return "\n".join(txt).strip()

def best_fuzzy_score(query: str, hay: str) -> int:
    """أعلى درجة بين partial_ratio و token_set_ratio بعد التطبيع."""
    q = normalize_ar(query)
    h = normalize_ar(hay)
    if not q or not h:
        return 0
    return max(fuzz.partial_ratio(q, h), fuzz.token_set_ratio(q, h))

def nationality_synonyms(raw: str):
    v = normalize_ar(raw)
    if not v: return []
    SAUDI = ["سعودي","سعوديه","saudi","ksa","saudi arabia","مواطن سعودي","سعودي الجنسيه"]
    NON   = ["غير سعودي","غيرسعودي","non saudi","nonsaudi","expat","وافد","غير سعودي الجنسيه","غير سعودي الجنسية"]
    if "غير" in v or "non" in v or "وافد" in v:
        return NON
    return SAUDI

# -------- واجهة --------
c1, c2 = st.columns(2)
with c1:
    uni = st.text_input("الجامعة", placeholder="مثال: جامعة الملك سعود")
with c2:
    major = st.text_input("التخصص", placeholder="مثال: نظم معلومات إدارية")
nation = st.text_input("الجنسية", placeholder="مثال: سعودي / غير سعودي / Saudi / Non-Saudi")

uploaded = st.file_uploader("أرفق ملفات (PDF فقط في التشخيص)", type=["pdf"], accept_multiple_files=True)

THRESH = 80  # ثابت ومخفي في النسخة النهائية

debug = st.checkbox("إظهار التشخيص التفصيلي (مقتطف نص + القيم بعد التطبيع)", value=True)

if st.button("ابدأ الفرز الآن"):
    if not uploaded:
        st.warning("فضلاً ارفع ملفاً واحداً على الأقل.")
    else:
        for up in uploaded:
            raw = up.read()
            text = read_pdf_text(raw)
            text_len = len(text)
            st.markdown(f"### {up.name}")
            st.caption(f"طول النص المستخرج: {text_len} حرف")

            if text_len == 0:
                st.error("لا يوجد نص مستخرج — غالبًا PDF عبارة عن صورة ممسوحة (يحتاج OCR).")
                continue

            # حساب الدرجات
            sc_uni   = best_fuzzy_score(uni, text)   if uni.strip()   else 100
            sc_major = best_fuzzy_score(major, text) if major.strip() else 100
            if nation.strip():
                keys = nationality_synonyms(nation)
                sc_nat = max([best_fuzzy_score(k, text) for k in keys]) if keys else best_fuzzy_score(nation, text)
            else:
                sc_nat = 100

            # عرض الدرجات
            colA, colB, colC = st.columns(3)
            colA.metric("الجامعة",  f"{sc_uni}%")
            colB.metric("التخصص",  f"{sc_major}%")
            colC.metric("الجنسية", f"{sc_nat}%")

            all_ok = all([
                sc_uni   >= THRESH,
                sc_major >= THRESH,
                sc_nat   >= THRESH
            ])

            if all_ok:
                st.success("✅ مطابق للشروط")
            else:
                st.error("❌ غير مطابق (واحد أو أكثر أقل من 80%)")

            if debug:
                with st.expander("مقتطف من النص (أول 1000 حرف)"):
                    st.code(text[:1000] or "لا يوجد نص", language="text")
                with st.expander("القيم بعد التطبيع (كيف نقارن)"):
                    st.write({
                        "university_input_norm": normalize_ar(uni),
                        "major_input_norm": normalize_ar(major),
                        "nation_input_norm": normalize_ar(nation),
                        "sample_text_norm_start": normalize_ar(text[:300])
                    })