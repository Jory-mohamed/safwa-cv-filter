import streamlit as st
import re, unicodedata, io, os
from pypdf import PdfReader
from rapidfuzz import fuzz
import pandas as pd

# =========================
# إعداد الصفحة (رسمي ومرتب)
# =========================
st.set_page_config(page_title="فلترة السير الذاتية", page_icon=None, layout="wide")

# ===== أنماط الواجهة (خلفية هادئة + نص واضح + لوقو زاوية + عنوان مركزي) =====
st.markdown(
    """
    <style>
    :root{
      --bg-soft:#f8fafc;       /* أبيض هادئ */
      --text:#0f172a;          /* نص داكن */
      --muted:#475569;         /* نص ثانوي */
      --navy:#0b2447;          /* نيڤي */
      --ok-bg:#e8f5e9; --ok-br:#2e7d32;
      --bad-bg:#ffebee; --bad-br:#c62828;
    }

    /* توحيد الخلفية وإلغاء أي تناقض في الثيم */
    html, body, .stApp, .block-container { background: var(--bg-soft) !important; }

    /* ألوان النصوص العامة */
    h1,h2,h3,h4,h5,h6,p,div,span,label,li { color: var(--text) !important; }
    .small, .caption, .st-emotion-cache-1y4p8pa { color: var(--muted) !important; }

    /* اللوقو في الزاوية العليا اليمنى */
    .corner { position: fixed; top: 16px; right: 16px; z-index: 1000; opacity:.98; pointer-events:none; }
    .corner img { width: 80px; height:auto; display:block; }

    /* عنوان مركزي */
    .title-wrap { text-align:center; margin-top: 18px; }
    .title { font-size: 34px; font-weight: 800; color: var(--navy); margin: 8px 0 4px 0; }
    .subtitle { font-size: 15px; color: var(--muted); margin-bottom: 18px; }

    /* صناديق النتائج */
    .result-ok  {background:var(--ok-bg);  border-left:6px solid var(--ok-br);  padding:12px 14px; border-radius:10px; margin:10px 0;}
    .result-bad {background:var(--bad-bg); border-left:6px solid var(--bad-br); padding:12px 14px; border-radius:10px; margin:10px 0;}

    /* شارات مختصرة */
    .badge {display:inline-block;padding:4px 10px;border-radius:999px;font-size:13px;margin:6px 6px 0 0;border:1px solid #e2e8f0}
    .ok   {background:#ecfdf5;color:#065f46;border-color:#a7f3d0}
    .bad  {background:#fef2f2;color:#991b1b;border-color:#fecaca}
    </style>
    """,
    unsafe_allow_html=True
)

# ===== اللوقو في الزاوية (إن وجد) باستخدام st.image لضمان الظهور) =====
def show_corner_logo():
    for path in ("logo.png", "assets/logo.png", "static/logo.png"):
        if os.path.exists(path):
            st.markdown('<div class="corner">', unsafe_allow_html=True)
            st.image(path, use_column_width=False)
            st.markdown('</div>', unsafe_allow_html=True)
            break
show_corner_logo()

# ===== عنوان مركزي + وصف مختصر بدون إيموجي =====
st.markdown('<div class="title-wrap"><div class="title">فلترة السير الذاتية الذكية</div><div class="subtitle">منصّة لفرز السير الذاتية</div></div>', unsafe_allow_html=True)
st.caption("Version: 3.4")

# =========================
# أدوات مساعدة
# =========================
def normalize_ar(text: str) -> str:
    if not text: return ""
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
        try: pages.append(p.extract_text() or "")
        except Exception: pages.append("")
    return "\n".join(pages)

def fuzzy_match(term: str, text: str, threshold: int = 80) -> (bool, int):
    if not term or not term.strip(): return None, 0
    norm_text = normalize_ar(text); norm_term = normalize_ar(term)
    score1 = fuzz.partial_ratio(norm_term, norm_text)
    score2 = fuzz.token_set_ratio(norm_term, norm_text)
    score = max(score1, score2)
    return (score >= threshold), int(score)

def evaluate_cv(text_raw: str, uni_req, major_req, major_syn, nat_req):
    THRESH = 80  # عتبة ثابتة
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
    kw_hits = [kw for kw in base_keywords if kw in norm_text]
    if len(kw_hits) >= 2:
        major_ok = True
        major_score = max(major_score, 90)
        syn_hits.append(" + ".join(kw_hits) + " (مطابقة مركّبة)")

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
    if st.button("تحقّق من CVات PDF"):
        if not pdf_files:
            st.warning("فضلاً ارفعي ملفًا واحدًا على الأقل.")
        else:
            for f in pdf_files:
                raw = extract_pdf_text(f.read())
                verdict, detail = evaluate_cv(raw, uni_req, major_req, major_syn, nat_req)
                box = "result-ok" if "✅" in verdict else "result-bad"
                st.markdown(f'<div class="{box}"><b>{f.name}</b> — {verdict}</div>', unsafe_allow_html=True)
                chips = "".join([
                    f'<span class="badge {"ok" if detail["الجامعة"]=="✅" else "bad"}">الجامعة: {detail["الجامعة"]} (score={detail["درجة الجامعة"]})</span>',
                    f'<span class="badge {"ok" if detail["التخصص"]=="✅" else "bad"}">التخصص: {detail["التخصص"]} (score={detail["درجة التخصص"]})</span>',
                    f'<span class="badge {"ok" if detail["الجنسية"]=="✅" else "bad"}">الجنسية: {detail["الجنسية"]} (score={detail["درجة الجنسية"]})</span>',
                ])
                st.markdown(chips, unsafe_allow_html=True)
                if detail.get("مطابقات التخصص"):
                    st.caption("مطابقات إضافية للتخصص: " + detail["مطابقات التخصص"])
                results.append({"اسم الملف": f.name, "النتيجة": verdict, **detail})

with tab2:
    st.subheader("رفع ملف Excel (xlsx)")
    excel_file = st.file_uploader("ملف Excel", type=["xlsx"], accept_multiple_files=False)
    if st.button("تحقّق من Excel"):
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
    if st.button("تحقّق من CSV"):
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
    st.dataframe(df, use_container_width=True)
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("تحميل النتائج CSV", csv, "نتائج_الفرز.csv", "text/csv")
