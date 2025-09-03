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
# ثيم مطابق للصورة (Navy + أبيض + أخضر)
# =========================
st.markdown("""
<style>
:root{
  --navy:#0b2447;       /* الخلفية الرئيسية */
  --navy-2:#081b36;     /* درجة أغمق للسايدبار/العناصر */
  --white:#ffffff;      /* كل النصوص */
  --muted:#d1d5db;      /* وصف */
  --green:#16a34a;      /* أزرار */
  --green-dark:#0f8a3d; /* تحويم */
  --ok-bg:rgba(22,163,74,.12);
  --ok-br:#22c55e;
  --bad-bg:rgba(239,68,68,.12);
  --bad-br:#ef4444;
}

/* خلفية كاملة Navy */
html, body, .stApp, .block-container { background: var(--navy) !important; }

/* شريط جانبي Navy أغمق */
section[data-testid="stSidebar"] { background: var(--navy-2) !important; }

/* كل النصوص أبيض */
h1,h2,h3,h4,h5,h6,p,div,span,label,li,small,code,em,strong { color: var(--white) !important; }

/* العنوان المركزي */
.title-wrap{ text-align:center; margin-top: 10px; }
.title{ font-size: 34px; font-weight: 800; color: var(--white); margin: 6px 0 4px 0; }
.subtitle{ font-size: 14px; color: var(--muted); }

/* اللوقو صغير بالزاوية العليا اليمنى */
.corner{ position: fixed; top: 14px; right: 16px; z-index: 1000; opacity:.96; pointer-events:none; }
.corner img{ width: 64px; height:auto; display:block; }

/* تبويبات بخط أبيض وحد سفلي أخضر عند التفعيل */
button[role="tab"]{ color: var(--muted) !important; background: transparent !important; border: 0 !important; }
button[role="tab"][aria-selected="true"]{ color: var(--white) !important; border-bottom: 3px solid var(--green) !important; }

/* حقول الإدخال داكنة وحدود فاتحة ونص أبيض */
input, textarea, .stTextInput input, .stTextArea textarea{
  color: var(--white) !important; background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(255,255,255,0.25) !important; border-radius: 10px !important;
}
div[data-baseweb="select"] > div{ background: rgba(255,255,255,0.06) !important; color: var(--white) !important; border-radius: 10px !important; }

/* رافع الملفات */
[data-testid="stFileUploader"] div{ color: var(--white) !important; }
[data-testid="stFileUploader"] section{ background: rgba(255,255,255,0.06) !important; border: 1px dashed rgba(255,255,255,0.25) !important; border-radius: 12px !important; }

/* الأزرار أخضر */
button[kind="primary"], .stDownloadButton>button{
  background: var(--green) !important; color: var(--white) !important; border: 0 !important; border-radius: 10px !important;
}
button[kind="primary"]:hover, .stDownloadButton>button:hover{ background: var(--green-dark) !important; }

/* صناديق النتائج */
.result-ok{ background: var(--ok-bg); border-left: 6px solid var(--ok-br); padding:12px 14px; border-radius:10px; margin:10px 0; }
.result-bad{ background: var(--bad-bg); border-left: 6px solid var(--bad-br); padding:12px 14px; border-radius:10px; margin:10px 0; }

/* جدول النتائج أبيض بنص داكن لسهولة القراءة */
[data-testid="stTable"], .stDataFrame, .stDataFrame div{ color: #111827 !important; }
</style>
""", unsafe_allow_html=True)

# ===== اللوقو الصغير (أعلى يمين) =====
def show_corner_logo():
    for path in ("logo.png", "assets/logo.png", "static/logo.png"):
        if os.path.exists(path):
            st.markdown('<div class="corner">', unsafe_allow_html=True)
            # use_container_width لتفادي تحذير use_column_width
            st.image(path, use_container_width=False)
            st.markdown('</div>', unsafe_allow_html=True)
            break
show_corner_logo()

# ===== عنوان في المنتصف ووصف مختصر =====
st.markdown('<div class="title-wrap"><div class="title">فلترة السير الذاتية الذكية</div><div class="subtitle">منصّة لفرز السير الذاتية</div></div>', unsafe_allow_html=True)
st.caption("Version: 3.5")

# =========================
# أدوات مساعدة
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
    uni_ok, uni_score   = fuzzy_match(uni_req,  norm_text, THRESH)
    nat_ok, nat_score   = fuzzy_match(nat_req,  norm_text, THRESH)
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

    base_keywords = ["نظم","معلومات"]
    if all(kw in norm_text for kw in base_keywords):
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
# إعداد المتطلبات (Sidebar)
# =========================
st.sidebar.header("إعداد المتطلبات")
uni_req   = st.sidebar.text_input("الجامعة المطلوبة", "جامعة الملك سعود")
major_req = st.sidebar.text_input("التخصص المطلوب", "نظم المعلومات الإدارية")
major_syn = st.sidebar.text_input("مرادفات التخصص (اختياري)", "إدارة نظم معلومات, MIS, Management Information Systems")
nat_req   = st.sidebar.text_input("الجنسية المطلوبة", "سعودي")

# =========================
# التبويبات
# =========================
tab1, tab2, tab3 = st.tabs(["رفع CVات PDF", "رفع ملف Excel", "رفع ملف CSV"])
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

# ===== تصدير النتائج =====
if results:
    df = pd.DataFrame(results)
    st.divider()
    st.dataframe(df, use_container_width=True)  # جدول أبيض بنص داكن للمقروئية
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("تحميل النتائج CSV", csv, "نتائج_الفرز.csv", "text/csv")
