import streamlit as st
import re, unicodedata, io, os
from pypdf import PdfReader
from rapidfuzz import fuzz
import pandas as pd

# =========================
# إعداد الصفحة
# =========================
st.set_page_config(page_title="فلترة السير الذاتية", page_icon=None, layout="wide")

# =========================
# ثيم (أبيض + نيڤي + أخضر) + ترتيب مخصص
# =========================
st.markdown("""
<style>
:root{
  --bg:#ffffff;
  --navy:#0b2447;
  --muted:#475569;
  --line:#e2e8f0;
  --green:#16a34a;
  --green-d:#0f8a3d;
  --ok-bg:#e8f5e9; --ok-br:#2e7d32;
  --bad-bg:#ffebee; --bad-br:#c62828;
}
html, body, .stApp, .block-container { background: var(--bg) !important; }

/* نص نيڤي */
h1,h2,h3,h4,h5,h6,p,div,span,label,li,small,strong { color: var(--navy) !important; }

/* اللوقو صغير بالزاوية العليا يمين */
.corner{ position: fixed; top: 12px; right: 16px; z-index: 1000; opacity:.98; pointer-events:none;}
.corner img{ width: 40px; height:auto; display:block; } /* غيّري الرقم لو تبينه أصغر/أكبر */

/* عنوان مركزي */
.title-wrap{ text-align:center; margin: 6px 0 10px 0; }
.title{ font-size: 34px; font-weight: 800; color: var(--navy); margin: 6px 0 2px 0; }
.subtitle{ font-size: 16px; color: var(--navy); font-weight:600;}
.subsubtitle{ font-size: 13px; color: var(--muted); }

/* بطاقة وسط لمدخلات الشروط */
.center-card{
  max-width: 640px; margin: 10px auto; padding: 16px 18px;
  background: #f8fafc; border: 1px solid var(--line); border-radius: 14px;
}

/* مدخلات أنيقة */
input, textarea, .stTextInput input, .stTextArea textarea{
  color: var(--navy) !important; background: #ffffff !important;
  border: 1px solid var(--line) !important; border-radius: 10px !important;
}
div[data-baseweb="select"] > div{ background: #ffffff !important; color: var(--navy) !important; border-radius: 10px !important; }

/* رافع الملفات (يسار) */
[data-testid="stFileUploader"] section{
  background: #f8fafc !important; border: 1px dashed var(--line) !important; border-radius: 12px !important;
}

/* تبويبات يسار */
button[role="tab"]{ color: var(--muted) !important; background: transparent !important; border: 0 !important; }
button[role="tab"][aria-selected="true"]{ color: var(--navy) !important; border-bottom: 3px solid var(--green) !important; }

/* أزرار خضراء */
button[kind="primary"], .stDownloadButton>button{
  background: var(--green) !important; color: #fff !important; border: 0 !important; border-radius: 10px !important;
}
button[kind="primary"]:hover, .stDownloadButton>button:hover{ background: var(--green-d) !important; }

/* صناديق النتائج */
.result-ok{ background: var(--ok-bg); border-left: 6px solid var(--ok-br); padding:12px 14px; border-radius:10px; margin:10px 0; }
.result-bad{ background: var(--bad-bg); border-left: 6px solid var(--bad-br); padding:12px 14px; border-radius:10px; margin:10px 0; }

/* جدول النتائج */
[data-testid="stTable"], .stDataFrame, .stDataFrame div{ color: #111827 !important; }
</style>
""", unsafe_allow_html=True)

# ===== اللوقو في الزاوية اليمنى =====
def show_corner_logo():
    for path in ("logo.png", "assets/logo.png", "static/logo.png"):
        if os.path.exists(path):
            st.markdown('<div class="corner">', unsafe_allow_html=True)
            st.image(path, use_container_width=False)
            st.markdown('</div>', unsafe_allow_html=True)
            break
show_corner_logo()

# ===== العنوان بالنص + السطرين =====
st.markdown(
    '<div class="title-wrap">'
    '<div class="title">فلترة السير الذاتية الذكية</div>'
    '<div class="subtitle">منصّة لفرز السير الذاتية</div>'
    '<div class="subsubtitle">صفوة — فلتر للسير الذاتية الذكي</div>'
    '</div>', unsafe_allow_html=True
)
st.caption("Version: 3.7")

# =========================
# أدوات مساعدة للفلترة
# =========================
def normalize_ar(text: str) -> str:
    if not text: return ""
    text = text.lower()
    text = ''.join(ch for ch in unicodedata.normalize('NFKD', text) if not unicodedata.combining(ch))
    text = re.sub(r"[أإآٱ]", "ا", text)
    text = text.replace("ة","ه").replace("ى","ي")
    text = re.sub(r"[^0-9a-z\u0600-\u06FF\\s]+", " ", text)
    text = re.sub(r"\\s+", " ", text).strip()
    return text

def extract_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for p in reader.pages:
        try: pages.append(p.extract_text() or "")
        except Exception: pages.append("")
    return "\\n".join(pages)

from rapidfuzz import fuzz
def fuzzy_match(term: str, text: str, threshold: int = 80) -> (bool, int):
    if not term or not term.strip(): return None, 0
    norm_text = normalize_ar(text); norm_term = normalize_ar(term)
    score1 = fuzz.partial_ratio(norm_term, norm_text)
    score2 = fuzz.token_set_ratio(norm_term, norm_text)
    score = max(score1, score2)
    return (score >= threshold), int(score)

def evaluate_cv(text_raw: str, uni_req, major_req, major_syn, nat_req):
    THRESH = 80
    norm_text = normalize_ar(text_raw)
    uni_ok, uni_score     = fuzzy_match(uni_req,  norm_text, THRESH)
    nat_ok, nat_score     = fuzzy_match(nat_req,  norm_text, THRESH)
    major_ok, major_score = fuzzy_match(major_req, norm_text, THRESH)

    syn_hits = []
    if major_syn.strip():
        for s in major_syn.split(","):
            term = s.strip()
            if not term: continue
            ok, score = fuzzy_match(term, norm_text, THRESH)
            if ok:
                major_ok = True
                major_score = max(major_score, score)
                syn_hits.append(f"{term} (score={score})")

    if all(kw in norm_text for kw in ["نظم","معلومات"]):
        major_ok = True
        major_score = max(major_score, 90)
        syn_hits.append("نظم + معلومات (مطابقة مركّبة)")

    req_flags = [x for x in [uni_ok, major_ok, nat_ok] if x is not None]
    all_ok = (len(req_flags) > 0) and all(req_flags)
    verdict = "مطابق للشروط ✅" if all_ok else "غير مطابق ❌"
    detail = {
        "الجامعة": "✅" if uni_ok else "❌",
        "التخصص": "✅" if major_ok else "❌",
        "الجنسية": "✅" if nat_ok else "❌",
        "درجة الجامعة": uni_score,
        "درجة التخصص": major_score,
        "درجة الجنسية": nat_score,
        "مطابقات التخصص": ", ".join(syn_hits) if syn_hits else ""
    }
    return verdict, detail

# =========================
# التخطيط: يسار (الرفع) — يمين (المدخلات بالوسط)
# =========================
left, right = st.columns([1, 2], gap="large")

# يسار: تبويبات الرفع
with left:
    tab1, tab2, tab3 = st.tabs(["رفع CVات PDF", "رفع ملف Excel", "رفع ملف CSV"])
    st.write("")  # مسافة بسيطة
    results = []

    with tab1:
        st.subheader("رفع CVات PDF")
        pdf_files = st.file_uploader("ملفات PDF", type=["pdf"], accept_multiple_files=True)
        if st.button("تحقّق من CVات PDF", type="primary"):
            if not pdf_files:
                st.warning("فضلاً ارفعي ملفًا واحدًا على الأقل.")
            else:
                for f in pdf_files:
                    raw = extract_pdf_text(f.read())
                    verdict, detail = evaluate_cv(raw, uni_req, major_req, major_syn, nat_req)
                    box = "result-ok" if "✅" in verdict else "result-bad"
                    st.markdown(f'<div class="{box}"><b>{f.name}</b> — {verdict}</div>', unsafe_allow_html=True)
                    results.append({"اسم الملف": f.name, "النتيجة": verdict, **detail})

    with tab2:
        st.subheader("رفع ملف Excel (xlsx)")
        excel_file = st.file_uploader("ملف Excel", type=["xlsx"], accept_multiple_files=False)
        if st.button("تحقّق من Excel", type="primary"):
            if not excel_file:
                st.warning("فضلاً ارفعي ملف Excel.")
            else:
                df = pd.read_excel(excel_file)
                for idx, row in df.iterrows():
                    text_raw = " ".join([str(v) for v in row.values if pd.notnull(v)])
                    verdict, detail = evaluate_cv(text_raw, uni_req, major_req, major_syn, nat_req)
                    box = "result-ok" if "✅" in verdict else "result-bad"
                    st.markdown(f'<div class="{box}"><b>صف {idx+1}</b> — {verdict}</div>', unsafe_allow_html=True)
                    results.append({"اسم الملف": f"صف {idx+1}", "النتيجة": verdict, **detail})

    with tab3:
        st.subheader("رفع ملف CSV")
        csv_file = st.file_uploader("ملف CSV", type=["csv"], accept_multiple_files=False)
        if st.button("تحقّق من CSV", type="primary"):
            if not csv_file:
                st.warning("فضلاً ارفعي ملف CSV.")
            else:
                df = pd.read_csv(csv_file)
                for idx, row in df.iterrows():
                    text_raw = " ".join([str(v) for v in row.values if pd.notnull(v)])
                    verdict, detail = evaluate_cv(text_raw, uni_req, major_req, major_syn, nat_req)
                    box = "result-ok" if "✅" in verdict else "result-bad"
                    st.markdown(f'<div class="{box}"><b>صف {idx+1}</b> — {verdict}</div>', unsafe_allow_html=True)
                    results.append({"اسم الملف": f"صف {idx+1}", "النتيجة": verdict, **detail})

# يمين: المدخلات بالنص داخل بطاقة وسط
with right:
    st.markdown('<div class="center-card">', unsafe_allow_html=True)
    st.markdown("### إعداد المتطلبات", unsafe_allow_html=True)
    uni_req   = st.text_input("الجامعة المطلوبة", "جامعة الملك سعود")
    major_req = st.text_input("التخصص المطلوب", "نظم المعلومات الإدارية")
    major_syn = st.text_input("مرادفات التخصص (اختياري)", "إدارة نظم معلومات, MIS, Management Information Systems")
    nat_req   = st.text_input("الجنسية المطلوبة", "سعودي")
    st.markdown('</div>', unsafe_allow_html=True)

# جدول النتائج والتنزيل
if 'results' in locals() and results:
    st.divider()
    df_out = pd.DataFrame(results)
    st.dataframe(df_out, use_container_width=True)
    csv = df_out.to_csv(index=False).encode('utf-8-sig')
    st.download_button("تحميل النتائج CSV", csv, "نتائج_الفرز.csv", "text/csv")
