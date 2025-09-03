import streamlit as st
import re, unicodedata, io, os
from pypdf import PdfReader
from rapidfuzz import fuzz
import pandas as pd

# ===== إعداد الصفحة =====
st.set_page_config(page_title="فلترة السير الذاتية", page_icon="🗂️", layout="wide")

# ===== أنماط الواجهة (خلفية بيضاء + لوقو في الزاوية) =====
st.markdown(
    '''
    <style>
    /* خلفية بيضاء بالكامل */
    .stApp, .block-container, body { background: #ffffff !important; }

    /* لوقو صغير في الزاوية العليا (يمين للـ RTL) */
    .corner-logo {
        position: fixed;
        top: 16px;
        right: 16px; /* لو تبينه يسار: استبدلي بـ left: 16px; وامسحي right */
        width: 84px; /* حجم قريب من لوقو الوزارات */
        height: auto;
        z-index: 1000;
        opacity: 0.98;
    }

    /* صندوق نتيجة مرتب */
    .result-ok   {background:#e8f5e9;border-left:6px solid #2e7d32;padding:12px 14px;border-radius:8px;margin:8px 0;}
    .result-bad  {background:#ffebee;border-left:6px solid #c62828;padding:12px 14px;border-radius:8px;margin:8px 0;}

    /* شارات */
    .badge {display:inline-block;padding:4px 10px;border-radius:999px;font-size:13px;margin-right:6px}
    .badge-ok {background:#e8f5e9;color:#1b5e20;border:1px solid #a5d6a7}
    .badge-bad{background:#ffebee;color:#b71c1c;border:1px solid #ef9a9a}
    </style>
    ''',
    unsafe_allow_html=True
)

st.title("🗂️ فلترة السير الذاتية")
st.caption("Version: 3.2 • خلفية بيضاء + لوقو في الزاوية • يدعم PDF + Excel + CSV • عتبة ثابتة 80 • تصدير النتائج")

# ===== عرض اللوقو في الزاوية إن وُجد =====
def show_corner_logo():
    logo_path = None
    for path in ("logo.png", "assets/logo.png", "static/logo.png"):
        if os.path.exists(path):
            logo_path = path
            break
    if logo_path:
        st.markdown(f'<img src="{logo_path}" class="corner-logo" />', unsafe_allow_html=True)

show_corner_logo()

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
    """مطابقة ذكية (Fuzzy) — العتبة ثابتة 80 داخل الاستدعاءات."""
    if not term or not term.strip():
        return None, 0
    norm_text = normalize_ar(text)
    norm_term = normalize_ar(term)
    score1 = fuzz.partial_ratio(norm_term, norm_text)
    score2 = fuzz.token_set_ratio(norm_term, norm_text)
    score = max(score1, score2)
    return (score >= threshold), int(score)

# ===== التحقق =====
def evaluate_cv(text_raw: str, uni_req, major_req, major_syn, nat_req):
    norm_text = normalize_ar(text_raw)
    THRESH = 80  # عتبة ثابتة

    # الجامعة والجنسية: Fuzzy
    uni_ok, uni_score = fuzzy_match(uni_req, norm_text, THRESH)
    nat_ok, nat_score = fuzzy_match(nat_req, norm_text, THRESH)

    # التخصص: Fuzzy + مرادفات + كلمات أساسية
    major_ok, major_score = fuzzy_match(major_req, norm_text, THRESH)
    syn_hits = []
    if major_syn.strip():
        for s in major_syn.split(","):
            term = s.strip()
            if not term:
                continue
            ok, score = fuzzy_match(term, norm_text, THRESH)
            if ok:
                major_ok = True
                major_score = max(major_score, score)
                syn_hits.append(f"{term} (score={score})")

    # كلمات أساسية عربية للتخصص (تقلل قبول الغلط)
    base_keywords = ["نظم", "معلومات"]
    kw_hits = [kw for kw in base_keywords if kw in norm_text]
    if len(kw_hits) >= 2:
        major_ok = True
        major_score = max(major_score, 90)
        syn_hits.append(" + ".join(kw_hits) + " (مطابقة مركّبة)")

    # الحكم النهائي
    req_flags = [x for x in [uni_ok, major_ok, nat_ok] if x is not None]
    all_ok = (len(req_flags) > 0) and all(req_flags)
    verdict = "✅ مطابق للشروط" if all_ok else "❌ غير مطابق"

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

# ===== خانات المتطلبات (Sidebar) =====
st.sidebar.header("⚙️ إعداد المتطلبات")
uni_req   = st.sidebar.text_input("🏫 الجامعة المطلوبة", "جامعة الملك سعود")
major_req = st.sidebar.text_input("📚 التخصص المطلوب", "نظم المعلومات الإدارية")
major_syn = st.sidebar.text_input("مرادفات التخصص (اختياري)", "إدارة نظم معلومات, MIS, Management Information Systems")
nat_req   = st.sidebar.text_input("🌍 الجنسية المطلوبة", "سعودي")

# ===== التبويبات =====
tab1, tab2, tab3 = st.tabs(["📂 رفع CVات PDF", "📊 رفع ملف Excel", "📑 رفع ملف CSV"])
results = []

# === تبويب 1: PDF ===
with tab1:
    st.subheader("📂 ارفعي ملفات الـ CV (PDF)")
    pdf_files = st.file_uploader("ملفات PDF", type=["pdf"], accept_multiple_files=True)
    if st.button("تحقّق من CVات PDF", type="primary"):
        if not pdf_files:
            st.warning("فضلاً ارفعي ملفًا واحدًا على الأقل.")
        else:
            for f in pdf_files:
                raw = extract_pdf_text(f.read())
                verdict, detail = evaluate_cv(raw, uni_req, major_req, major_syn, nat_req)
                box_class = "result-ok" if "✅" in verdict else "result-bad"
                st.markdown(f'<div class="{box_class}"><b>النتيجة:</b> {verdict} — {f.name}</div>', unsafe_allow_html=True)
                chips = "".join([
                    f'<span class="badge {"badge-ok" if detail["الجامعة"]=="✅" else "badge-bad"}">الجامعة: {detail["الجامعة"]} (score={detail["درجة الجامعة"]})</span>',
                    f'<span class="badge {"badge-ok" if detail["التخصص"]=="✅" else "badge-bad"}">التخصص: {detail["التخصص"]} (score={detail["درجة التخصص"]})</span>',
                    f'<span class="badge {"badge-ok" if detail["الجنسية"]=="✅" else "badge-bad"}">الجنسية: {detail["الجنسية"]} (score={detail["درجة الجنسية"]})</span>',
                ])
                st.markdown(chips, unsafe_allow_html=True)
                if detail.get("مطابقات التخصص"):
                    st.caption("مطابقات إضافية للتخصص: " + detail["مطابقات التخصص"])
                results.append({"اسم الملف": f.name, "النتيجة": verdict, **detail})

# === تبويب 2: Excel ===
with tab2:
    st.subheader("📊 ارفعي ملف Excel (xlsx)")
    excel_file = st.file_uploader("ملف Excel", type=["xlsx"], accept_multiple_files=False)
    if st.button("تحقّق من Excel", type="primary"):
        if not excel_file:
            st.warning("فضلاً ارفعي ملف Excel.")
        else:
            df = pd.read_excel(excel_file)
            for idx, row in df.iterrows():
                text_raw = " ".join([str(v) for v in row.values if pd.notnull(v)])
                verdict, detail = evaluate_cv(text_raw, uni_req, major_req, major_syn, nat_req)
                box_class = "result-ok" if "✅" in verdict else "result-bad"
                st.markdown(f'<div class="{box_class}"><b>صف {idx+1}:</b> {verdict}</div>', unsafe_allow_html=True)
                chips = "".join([
                    f'<span class="badge {"badge-ok" if detail["الجامعة"]=="✅" else "badge-bad"}">الجامعة: {detail["الجامعة"]} (score={detail["درجة الجامعة"]})</span>',
                    f'<span class="badge {"badge-ok" if detail["التخصص"]=="✅" else "badge-bad"}">التخصص: {detail["التخصص"]} (score={detail["درجة التخصص"]})</span>',
                    f'<span class="badge {"badge-ok" if detail["الجنسية"]=="✅" else "badge-bad"}">الجنسية: {detail["الجنسية"]} (score={detail["درجة الجنسية"]})</span>',
                ])
                st.markdown(chips, unsafe_allow_html=True)
                if detail.get("مطابقات التخصص"):
                    st.caption("مطابقات إضافية للتخصص: " + detail["مطابقات التخصص"])
                results.append({"اسم الملف": f"صف {idx+1}", "النتيجة": verdict, **detail})

# === تبويب 3: CSV ===
with tab3:
    st.subheader("📑 ارفعي ملف CSV")
    csv_file = st.file_uploader("ملف CSV", type=["csv"], accept_multiple_files=False)
    if st.button("تحقّق من CSV", type="primary"):
        if not csv_file:
            st.warning("فضلاً ارفعي ملف CSV.")
        else:
            df = pd.read_csv(csv_file)
            for idx, row in df.iterrows():
                text_raw = " ".join([str(v) for v in row.values if pd.notnull(v)])
                verdict, detail = evaluate_cv(text_raw, uni_req, major_req, major_syn, nat_req)
                box_class = "result-ok" if "✅" in verdict else "result-bad"
                st.markdown(f'<div class="{box_class}"><b>صف {idx+1}:</b> {verdict}</div>', unsafe_allow_html=True)
                chips = "".join([
                    f'<span class="badge {"badge-ok" if detail["الجامعة"]=="✅" else "badge-bad"}">الجامعة: {detail["الجامعة"]} (score={detail["درجة الجامعة"]})</span>',
                    f'<span class="badge {"badge-ok" if detail["التخصص"]=="✅" else "badge-bad"}">التخصص: {detail["التخصص"]} (score={detail["درجة التخصص"]})</span>',
                    f'<span class="badge {"badge-ok" if detail["الجنسية"]=="✅" else "badge-bad"}">الجنسية: {detail["الجنسية"]} (score={detail["درجة الجنسية"]})</span>',
                ])
                st.markdown(chips, unsafe_allow_html=True)
                if detail.get("مطابقات التخصص"):
                    st.caption("مطابقات إضافية للتخصص: " + detail["مطابقات التخصص"])
                results.append({"اسم الملف": f"صف {idx+1}", "النتيجة": verdict, **detail})

# ===== زر تحميل النتائج =====
if results:
    df = pd.DataFrame(results)
    st.divider()
    st.dataframe(df, use_container_width=True)
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("⬇️ تحميل النتائج كـ CSV", csv, "نتائج_الفرز.csv", "text/csv")
