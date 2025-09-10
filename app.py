# app.py
import streamlit as st
from pathlib import Path
import pdfplumber, docx2txt, re, io
from rapidfuzz import fuzz

# ---------------- Page ----------------
st.set_page_config(page_title="صفوة | فرز السير الذاتية", page_icon=":mag_right:")

# ---------------- Helpers ----------------
AR_DIAC = r"[\u0617-\u061A\u064B-\u0652\u0654\u0655\u0670\u0640]"  # الحركات والتطويل

def normalize_ar(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    # حروف موحّدة
    s = re.sub("[إأآا]", "ا", s)
    s = re.sub("ى", "ي", s)
    s = re.sub("ؤ", "و", s)
    s = re.sub("ئ", "ي", s)
    s = re.sub("ة", "ه", s)
    # إزالة حركات/تطويل ورموز
    s = re.sub(AR_DIAC, "", s)
    s = re.sub(r"[^\w\s\u0600-\u06FF]", " ", s)  # أبقي العربية والمسافات
    s = re.sub(r"\s+", " ", s).strip()
    return s

def read_file(file) -> str:
    name = (file.name or "").lower()
    if name.endswith(".pdf"):
        try:
            with pdfplumber.open(file) as pdf:
                pages = []
                for p in pdf.pages:
                    t = p.extract_text() or ""
                    pages.append(t)
                text = "\n".join(pages)
        except Exception:
            text = ""
    elif name.endswith(".docx"):
        # docx2txt يحتاج مسار أو بايتات: نحفظ مؤقتًا
        data = file.read()
        text = docx2txt.process(io.BytesIO(data))
    else:
        text = file.read().decode("utf-8", errors="ignore")
    return text or ""

def best_ratio(needle: str, hay: str) -> int:
    """
    نرجّع أعلى نسبة تطابق باستخدام token_set_ratio.
    إذا النص طويل، نكتفي بأنه موجود مباشرة ليكون 100%.
    """
    if not needle:
        return 0
    if needle in hay:
        return 100
    # fuzzy
    return fuzz.token_set_ratio(needle, hay)

def decide(university_in, major_in, nation_in, text_norm, thresh=80):
    uni = normalize_ar(university_in)
    maj = normalize_ar(major_in)
    nat = normalize_ar(nation_in)

    # نسب التطابق لكل شرط
    uni_score = best_ratio(uni, text_norm) if uni else 100
    maj_score = best_ratio(maj, text_norm) if maj else 100
    nat_score = best_ratio(nat, text_norm) if nat else 100

    return uni_score, maj_score, nat_score, (
        uni_score >= thresh and maj_score >= thresh and nat_score >= thresh
    )

# ---------------- UI ----------------
st.markdown(
    """
    <div style="text-align:center;margin-top:10px">
      <img src="static/logo.png" alt="Safwa" style="width:84px;height:84px;border-radius:14px;"/>
      <h1 style="margin:8px 0 0">صفوة</h1>
      <div style="opacity:.75">تميّز بخطوة</div>
    </div>
    """,
    unsafe_allow_html=True,
)

THRESH = 80  # ثابت ومخفي

colA, colB = st.columns(2)
with colA:
    university_in = st.text_input("الجامعة", placeholder="مثال: جامعة الملك سعود")
with colB:
    major_in = st.text_input("التخصص", placeholder="مثال: نظم المعلومات الإدارية")

nation_in = st.text_input("الجنسية", placeholder="مثال: سعودي")

st.markdown("**✨ ارفع سيرتك (PDF أو DOCX)**")
uploaded_files = st.file_uploader(
    "Drag & drop", type=["pdf", "docx"], accept_multiple_files=True, label_visibility="collapsed"
)

if uploaded_files:
    # نظهر تنبيه لو النص المستخرج ضعيف
    for file in uploaded_files:
        raw = read_file(file)
        text_norm = normalize_ar(raw)

        # لو النص المستخرج قليل (PDF مصوّر غالبًا)
        if len(text_norm) < 80 and file.name.lower().endswith(".pdf"):
            st.warning("الملف يبدو PDF مصوّر (نص قليل). جرّب DOCX أو PDF نصّي.", icon="⚠️")

        uni_score, maj_score, nat_score, ok = decide(
            university_in, major_in, nation_in, text_norm, THRESH
        )

        with st.container(border=True):
            st.subheader(file.name)
            col1, col2, col3 = st.columns(3)
            col1.metric("الجامعة", f"{uni_score:.2f}%")
            col2.metric("التخصص", f"{maj_score:.2f}%")
            col3.metric("الجنسية", f"{nat_score:.2f}%")

            if ok:
                st.success("مطابق للشروط ✅ (كلها ≥ 80%)")
            else:
                st.error("غير مطابق ❌ (أحد الشروط أقل من 80%)")

            with st.expander("مقتطف من النص (أوّل 700 حرف)"):
                st.code((raw or "")[:700])

            with st.expander("القيم بعد التطبيع (للمقارنة)"):
                st.json(
                    {
                        "university_input_norm": normalize_ar(university_in),
                        "major_input_norm": normalize_ar(major_in),
                        "nation_input_norm": normalize_ar(nation_in),
                        "sample_text_norm_start": text_norm[:300],
                    }
                )

# ---------------- Style ----------------
def inject_css(path="static/style.css"):
    p = Path(path)
    if p.exists():
        st.markdown(f"<style>{p.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

inject_css()