import streamlit as st
import pandas as pd
import io, re, zipfile
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pdfplumber
import arabic_reshaper
from bidi.algorithm import get_display
from rapidfuzz import fuzz

# ── إعداد الصفحة ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="صفوة | فرز السير الذاتية", page_icon="🔎", layout="centered")

PRIMARY = "#0F1A2E"   # كحلي (navy)
BG_PAGE = "#FFFFFF"   # خلفية الصفحة: أبيض
INPUT_BG = "#FAF3E8"  # خلفية الحقول: كريمي هادئ
TEXT     = "#111111"  # نص غامق واضح
MUTED    = "#6B7280"  # نص ثانوي
GOOD     = "#2F855A"
WARN     = "#B45309"
BAD      = "#9B1C1C"

# حمّل style.css إن وجد
try:
    with open("style.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except Exception:
    # Fallback بسيط يكفي لإظهار النص بلون واضح وخلفية كريمية للمدخلات
    st.markdown(f"""
    <style>
      html, body, [class*="css"] {{
        direction: rtl; background:{BG_PAGE}; color:{TEXT};
        font-family: "Inter", system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      }}
      .block-container {{ padding-top: 2rem; max-width: 900px; }}
      h1,h2,h3 {{ color:{PRIMARY}; }}
      .card {{
        background:#FFFFFF; border:1px solid rgba(0,0,0,.06); border-radius:14px; padding:16px;
        box-shadow:0 2px 10px rgba(0,0,0,.04);
      }}
      .stTextInput>div>div>input {{
        background:{INPUT_BG} !important; color:{TEXT} !important; border-radius:12px;
      }}
      .stFileUploader>div {{
        background:{INPUT_BG} !important; border-radius:12px;
      }}
      .stButton>button {{ background:{PRIMARY}; color:#fff; border-radius:12px; font-weight:600; height:44px; }}
      .small {{ color:{MUTED}; font-size:12px }}
    </style>
    """, unsafe_allow_html=True)

# ── دوال مساعدة ────────────────────────────────────────────────────────────────
ARABIC_DIACRITICS = re.compile(r'[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]')

def normalize_arabic(s: str) -> str:
    if not s: return ""
    s = s.strip()
    s = ARABIC_DIACRITICS.sub('', s)
    s = (s.replace('أ','ا').replace('إ','ا').replace('آ','ا')
           .replace('ى','ي').replace('ئ','ي').replace('ؤ','و').replace('ة','ه'))
    s = re.sub(r'\s+', ' ', s)
    return s

def fuzzy_score(needle: str, haystack: str) -> int:
    if not needle or not haystack: return 0
    return fuzz.partial_ratio(needle.lower(), haystack.lower())

def read_txt(file) -> str:
    try:
        data = file.read()
        for enc in ("utf-8", "windows-1256", "latin-1"):
            try: return data.decode(enc, errors="ignore")
            except Exception: continue
        return data.decode("utf-8", errors="ignore")
    except Exception: return ""

def read_docx(file) -> str:
    try:
        data = file.read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            with z.open('word/document.xml') as d:
                xml = d.read().decode('utf-8', errors='ignore')
        text = re.sub(r'</w:p>', '\n', xml)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text
    except Exception: return ""

def read_pdf_arabic(file) -> str:
    try:
        data = file.read()
        out = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for p in pdf.pages:
                t = p.extract_text() or ""
                t = re.sub(r'\s+', ' ', t)
                # reshape + bidi للعرض العربي
                t = get_display(arabic_reshaper.reshape(t))
                out.append(t)
        return normalize_arabic("\n".join(out))
    except Exception: return ""

def read_xlsx(file) -> str:
    try:
        df = pd.read_excel(file).fillna("")
        return " ".join(df.astype(str).values.ravel().tolist())
    except Exception: return ""

def get_file_text(sf) -> str:
    name = (sf.name or "").lower()
    sf.seek(0)
    if name.endswith(".txt"):
        return normalize_arabic(read_txt(sf))
    if name.endswith(".docx"):
        sf.seek(0); return normalize_arabic(read_docx(sf))
    if name.endswith(".pdf"):
        sf.seek(0); return read_pdf_arabic(sf)  # داخله normalize
    if name.endswith(".xlsx"):
        sf.seek(0); return normalize_arabic(read_xlsx(sf))
    # امتداد غير مدعوم كنص: استخدم الاسم
    return normalize_arabic(name)

def file_size_kb(sf) -> int:
    try:
        sf.seek(0, 2); size = sf.tell(); sf.seek(0); return int(size/1024)
    except Exception: return 0

# ── الواجهة ───────────────────────────────────────────────────────────────────
# (لو عندك logo.png احفظيه بجانب app.py ويظهر هنا تلقائيًا)
try:
    st.image("logo.png", width=120)
except Exception:
    pass

st.markdown("## صفوة – فرز السير الذاتية 🔎")
st.markdown('<div class="small">املئي الحقول، ارفعي الملفات، واضغطي «فرّز». ثم نزّلي النتائج بصيغ CSV/XLSX/PDF.</div>', unsafe_allow_html=True)

with st.form("filter_form", clear_on_submit=False):
    university = st.text_input("الجامعة", placeholder="مثال: جامعة الملك سعود / KSU")
    major      = st.text_input("التخصص", placeholder="مثال: نظم المعلومات الإدارية / MIS")
    nationality= st.text_input("الجنسية", placeholder="مثال: سعودي/سعودية")
    uploaded = st.file_uploader(
        "ارفعي السير الذاتية (PDF / DOCX / TXT / XLSX) — تقدرين ترفعين أكثر من ملف",
        type=["pdf","docx","txt","xlsx"], accept_multiple_files=True
    )
    submitted = st.form_submit_button("فرّز ✅")

THRESHOLD = 80  # حد التشابه يعتبر مطابقة

if submitted:
    if not uploaded:
        st.warning("ارفعي ملفات أولًا.")
    else:
        uni_q = normalize_arabic(university)
        maj_q = normalize_arabic(major)
        nat_q = normalize_arabic(nationality)

        rows, errors = [], []

        for f in uploaded:
            try:
                ext = (f.name.split(".")[-1]).lower() if "." in f.name else ""
                text = get_file_text(f)

                uni_score = fuzzy_score(uni_q, text) if uni_q else 0
                maj_score = fuzzy_score(maj_q, text) if maj_q else 0
                nat_score = fuzzy_score(nat_q, text) if nat_q else 0

                hits = sum(s >= THRESHOLD for s in [uni_score, maj_score, nat_score])
                if hits == 3:
                    decision, badge = "مطابق قوي", GOOD
                elif hits == 2:
                    decision, badge = "مطابق مبدئي", WARN
                else:
                    decision, badge = "غير مطابق", BAD

                rows.append({
                    "الملف": f.name,
                    "النوع": ext.upper(),
                    "الحجم KB": file_size_kb(f),
                    "درجة الجامعة": uni_score,
                    "درجة التخصص": maj_score,
                    "درجة الجنسية": nat_score,
                    "عدد التطابقات": hits,
                    "القرار": decision
                })
            except Exception as e:
                errors.append(f"تعذّر معالجة {f.name}: {e}")

        if errors:
            st.info("تم تجاهل بعض الملفات بسبب أخطاء، والباقي تمت معالجته:")
            for msg in errors:
                st.caption(f"• {msg}")

        if rows:
            results_df = pd.DataFrame(rows)
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### النتائج")
            st.dataframe(results_df, use_container_width=True)

            # تنزيل CSV
            csv_buf = io.StringIO()
            results_df.to_csv(csv_buf, index=False)
            st.download_button(
                "⬇️ تنزيل CSV",
                data=csv_buf.getvalue().encode("utf-8-sig"),
                file_name=f"results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv", use_container_width=True
            )

            # تنزيل XLSX
            xlsx_buf = io.BytesIO()
            with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
                results_df.to_excel(writer, index=False, sheet_name="Results")
            st.download_button(
                "⬇️ تنزيل Excel (XLSX)",
                data=xlsx_buf.getvalue(),
                file_name=f"results_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            # تنزيل PDF (جدول مبسّط)
            pdf_buf = io.BytesIO()
            with PdfPages(pdf_buf) as pdf:
                fig, ax = plt.subplots(figsize=(11.69, 8.27))  # قرابة A4 landscape
                ax.axis('off')
                ax.set_title("تقرير فرز السير الذاتية — صفوة", fontsize=14, pad=14)
                show_df = results_df.copy()
                max_rows = 30
                if len(show_df) > max_rows:
                    show_df = show_df.iloc[:max_rows]
                table = ax.table(cellText=show_df.values, colLabels=show_df.columns,
                                 loc='center', cellLoc='center')
                table.auto_set_font_size(False)
                table.set_fontsize(7)
                table.scale(1, 1.2)
                ax.text(0.5, 0.04, f"أُنشئ في: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        ha='center', va='center', fontsize=9, color="#555")
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)

            st.download_button(
                "⬇️ تنزيل PDF",
                data=pdf_buf.getvalue(),
                file_name=f"results_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf", use_container_width=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("ما في نتائج لعرضها.")