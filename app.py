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

# OCR deps (قد تكون غير متوفرة على الاستضافة)
OCR_AVAILABLE = True
try:
    import pytesseract
    from PIL import Image
    import fitz  # PyMuPDF
    # نحاول نقرأ إصدار تيسيراكت لمعرفة التوفر الحقيقي
    try:
        _ = pytesseract.get_tesseract_version()
    except Exception:
        OCR_AVAILABLE = False
except Exception:
    OCR_AVAILABLE = False

# ── تثبيت الصفحة + ستايل قوي (يجبر الأبيض والنص الأسود) ─────────────
st.set_page_config(page_title="صفوة | فرز السير الذاتية", page_icon="🔎", layout="centered")
st.markdown("""
<style>
body, .stApp { background:#FFFFFF !important; color:#111111 !important; }
.block-container { padding-top: 1.5rem; max-width: 960px; }
h1,h2,h3 { color:#0F1A2E !important; }
.stTextInput>div>div>input { background:#FAF3E8 !important; color:#111 !important; border-radius:12px; }
.stFileUploader>div { background:#FAF3E8 !important; border-radius:12px; }
.stButton>button { background:#0F1A2E; color:#fff; border-radius:12px; font-weight:600; height:44px; }
.dataframe td, .dataframe th { text-align:center; }
.small { color:#6B7280; font-size:12px; }
.card { background:#FFF; border:1px solid rgba(0,0,0,.06); border-radius:14px; padding:16px; box-shadow:0 2px 10px rgba(0,0,0,.04); }
</style>
""", unsafe_allow_html=True)

# ── أدوات عربية + Fuzzy ────────────────────────────────────────
ARABIC_DIACRITICS = re.compile(r'[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]')
def normalize_ar(s: str) -> str:
    if not s: return ""
    s = s.strip()
    s = ARABIC_DIACRITICS.sub('', s)
    s = (s.replace('أ','ا').replace('إ','ا').replace('آ','ا')
           .replace('ى','ي').replace('ئ','ي').replace('ؤ','و').replace('ة','ه'))
    s = re.sub(r'\s+', ' ', s)
    return s

def fuzzy_score(needle: str, haystack: str) -> int:
    from rapidfuzz import fuzz
    if not needle or not haystack: return 0
    return fuzz.partial_ratio(needle.lower(), haystack.lower())

# ── قرّاءات الملفات ────────────────────────────────────────────
def read_txt(file) -> str:
    try:
        data = file.read()
        for enc in ("utf-8","windows-1256","latin-1"):
            try: return data.decode(enc, errors="ignore")
            except: pass
        return data.decode("utf-8", errors="ignore")
    except: return ""

def read_docx(file) -> str:
    try:
        data = file.read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            with z.open('word/document.xml') as d:
                xml = d.read().decode('utf-8', errors='ignore')
        text = re.sub(r'</w:p>', '\n', xml)
        text = re.sub(r'<[^>]+>', ' ', text)
        return re.sub(r'\s+', ' ', text)
    except: return ""

def read_pdf_text(file) -> str:
    """استخراج نص PDF بمحاولة عربية (بدون OCR)."""
    try:
        data = file.read()
        out = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for p in pdf.pages:
                t = p.extract_text() or ""
                t = re.sub(r'\s+', ' ', t)
                t = get_display(arabic_reshaper.reshape(t))
                out.append(t)
        return normalize_ar("\n".join(out))
    except:
        return ""

def read_pdf_ocr(file) -> str:
    """OCR احتياطي، يعمل فقط لو تيسيراكت متاح."""
    if not OCR_AVAILABLE:
        return ""
    try:
        data = file.read()
        doc = fitz.open(stream=data, filetype="pdf")
        parts = []
        for page in doc:
            pix = page.get_pixmap(dpi=220)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            t = pytesseract.image_to_string(img, lang="ara+eng")
            parts.append(t)
        return normalize_ar("\n".join(parts))
    except:
        return ""

def read_xlsx(file) -> str:
    try:
        df = pd.read_excel(file).fillna("")
        return " ".join(df.astype(str).values.ravel().tolist())
    except:
        return ""

def safe_text_for(sf, use_ocr: bool) -> tuple[str, str]:
    """
    يرجّع (text, source_note)
    source_note يشرح من وين جاب النص: نص PDF / OCR / DOCX / TXT / اسم ملف فقط
    """
    name = (sf.name or "").lower()
    sf.seek(0)
    if name.endswith(".txt"):
        return normalize_ar(read_txt(sf)), "TXT"
    if name.endswith(".docx"):
        sf.seek(0); return normalize_ar(read_docx(sf)), "DOCX"
    if name.endswith(".xlsx"):
        sf.seek(0); return normalize_ar(read_xlsx(sf)), "XLSX"
    if name.endswith(".pdf"):
        sf.seek(0); txt = read_pdf_text(sf)
        if (not txt or len(txt) < 30) and use_ocr:
            sf.seek(0); ocr = read_pdf_ocr(sf)
            if ocr:
                return ocr, ("PDF + OCR" if OCR_AVAILABLE else "PDF (OCR غير متاح)")
        if txt:
            return txt, "PDF (نص)"
        # فشلنا بالنص و/أو OCR: استخدم اسم الملف عالأقل
        return normalize_ar(name), "اسم الملف (تعذر قراءة النص)"
    # امتدادات أخرى: اسم الملف
    return normalize_ar(name), "اسم الملف"

def file_size_kb(sf) -> int:
    try:
        sf.seek(0, 2); size = sf.tell(); sf.seek(0); return int(size/1024)
    except: return 0

# ── واجهة ──────────────────────────────────────────────────────
st.markdown("## صفوة – فرز السير الذاتية 🔎")
st.markdown('<div class="small">املئي الحقول، ارفعي الملفات، واضغطي «فرّز». بعدين تقدرين تنزلين CSV / XLSX / PDF.</div>', unsafe_allow_html=True)

# حالة الـ OCR
if OCR_AVAILABLE:
    st.success("OCR: جاهز ✅ (Tesseract متوفر)")
else:
    st.info("OCR: غير متاح على هذه البيئة. بنحاول نص PDF أول، وإذا فشل نطابق على اسم الملف. (نقدر نفعّله لاحقًا).")

with st.form("f", clear_on_submit=False):
    u = st.text_input("الجامعة", placeholder="مثال: جامعة الملك سعود / KSU")
    m = st.text_input("التخصص", placeholder="مثال: نظم المعلومات الإدارية / MIS")
    n = st.text_input("الجنسية", placeholder="مثال: سعودي/سعودية")
    files = st.file_uploader("ارفعي السير الذاتية (PDF / DOCX / TXT / XLSX)", type=["pdf","docx","txt","xlsx"], accept_multiple_files=True)
    use_ocr = st.checkbox("تفعيل OCR للـPDF عند الحاجة", value=True)
    submit = st.form_submit_button("فرّز ✅")

THRESHOLD = 80

if submit:
    if not files:
        st.warning("ارفعي ملفات أولًا.")
    else:
        uq, mq, nq = normalize_ar(u), normalize_ar(m), normalize_ar(n)
        rows = []
        previews = []  # للمعاينات

        for f in files:
            ext = (f.name.split(".")[-1]).upper() if "." in f.name else ""
            try:
                text, source = safe_text_for(f, use_ocr and OCR_AVAILABLE)
                # لو ما فيه نص معقول، خذ اسم الملف already done inside
                uni = fuzzy_score(uq, text) if uq else 0
                maj = fuzzy_score(mq, text) if mq else 0
                nat = fuzzy_score(nq, text) if nq else 0
                hits = sum(s >= THRESHOLD for s in [uni, maj, nat])

                if hits == 3: decision = "مطابق قوي"
                elif hits == 2: decision = "مطابق مبدئي"
                else: decision = "غير مطابق"

                rows.append({
                    "الملف": f.name,
                    "النوع": ext,
                    "الحجم KB": file_size_kb(f),
                    "درجة الجامعة": uni,
                    "درجة التخصص": maj,
                    "درجة الجنسية": nat,
                    "عدد التطابقات": hits,
                    "القرار": decision,
                    "المصدر": source
                })

                previews.append((f.name, text[:180] + ("…" if len(text) > 180 else "")))

            except Exception as e:
                rows.append({
                    "الملف": f.name, "النوع": ext, "الحجم KB": file_size_kb(f),
                    "درجة الجامعة": 0, "درجة التخصص": 0, "درجة الجنسية": 0,
                    "عدد التطابقات": 0, "القرار": "خطأ بالمعالجة", "المصدر": f"Exception: {e}"
                })
                previews.append((f.name, ""))

        df = pd.DataFrame(rows)
        st.markdown("### النتائج")
        st.dataframe(df, use_container_width=True)

        # معاينات النص المقروء
        with st.expander("معاينة النص المقروء لكل ملف (للتشخيص)"):
            for name, snip in previews:
                st.markdown(f"**{name}**")
                st.code(snip or "—")

        # تنزيلات
        # CSV
        csv_buf = io.StringIO(); df.to_csv(csv_buf, index=False)
        st.download_button("⬇️ CSV", data=csv_buf.getvalue().encode("utf-8-sig"),
                           file_name=f"results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv")
        # XLSX
        xlsx_buf = io.BytesIO()
        with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Results")
        st.download_button("⬇️ Excel (XLSX)", data=xlsx_buf.getvalue(),
                           file_name=f"results_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        # PDF
        pdf_buf = io.BytesIO()
        with PdfPages(pdf_buf) as pdf:
            fig, ax = plt.subplots(figsize=(11.69, 8.27))
            ax.axis('off')
            ax.set_title("تقرير فرز السير الذاتية — صفوة", fontsize=14, pad=14)
            show_df = df.copy()
            if len(show_df) > 30: show_df = show_df.iloc[:30]
            tbl = ax.table(cellText=show_df.values, colLabels=show_df.columns, loc='center', cellLoc='center')
            tbl.auto_set_font_size(False); tbl.set_fontsize(7); tbl.scale(1, 1.2)
            ax.text(0.5, 0.04, f"أُنشئ في: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    ha='center', va='center', fontsize=9, color="#555")
            pdf.savefig(fig, bbox_inches='tight'); plt.close(fig)
        st.download_button("⬇️ PDF", data=pdf_buf.getvalue(),
                           file_name=f"results_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf")