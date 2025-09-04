import streamlit as st

# ===== Page Config =====
st.set_page_config(
    page_title="صفوة لفرز السير الذاتيه",
    page_icon="🗂️",
    layout="wide"
)

# ===== Session State (format toggle & reset) =====
if "format_active" not in st.session_state:
    st.session_state.format_active = "XLSX"
if "preset" not in st.session_state:
    st.session_state.preset = "Preset (KSU + MIS)"
if "uni" not in st.session_state:
    st.session_state.uni = "King Saud University"
if "nation" not in st.session_state:
    st.session_state.nation = "سعودية"
if "major" not in st.session_state:
    st.session_state.major = "نظم المعلومات الإدارية، علوم حاسب…"
if "extra" not in st.session_state:
    st.session_state.extra = ""

def set_active(fmt: str):
    st.session_state.format_active = fmt

def do_reset():
    st.session_state.format_active = "XLSX"
    st.session_state.preset = "Preset (KSU + MIS)"
    st.session_state.uni = ""
    st.session_state.nation = ""
    st.session_state.major = ""
    st.session_state.extra = ""
    st.session_state.uploaded_files = None

# ===== Styles (CSS) =====
css = """
<style>
:root{
  --bg:#FFFFFF;
  --ink:#182A4E;        /* كحلي العناوين */
  --sub:#6B7280;        /* نص ثانوي */
  --muted:#BEC1C4;      /* الرمادي المتفق عليه */
  --field:#F3F4F5;      /* خلفية الحقول */
  --accent:#3B7C74;     /* الأخضر للأزرار */
  --accent-ink:#FFFFFF;
  --card:#0f1f3d;       /* الكارد الداكن (السايدبار) */
  --border:#E5E7EB;
  --radius:12px;
  --shadow:0 6px 20px rgba(0,0,0,.06);
}

html, body { background: var(--bg); }
[data-testid="stAppViewContainer"] > .main { padding-top: 0; }

.rtl-wrap { direction: rtl; font-family: system-ui,-apple-system,"Segoe UI","Noto Sans Arabic","Cairo","Tahoma",sans-serif; color: var(--ink); }

.site-header{
  display:flex;align-items:center;justify-content:space-between;
  padding:16px 8px 12px;border-bottom:1px solid var(--border);
}

.brand{
  display:flex;align-items:center;gap:12px;
  flex-direction: row-reverse; /* لوقو يمين ثم العنوان */
}

.header-logo{
  height:35px;width:auto;object-fit:contain;
}
@media (min-width:1024px){
  .header-logo{height:50px}
}

.brand-title{
  font-weight:800;font-size:20px;letter-spacing:.2px;color:var(--ink);
}
@media (min-width:1024px){
  .brand-title{font-size:22px}
}

/* Grid Layout */
.grid{
  display:grid;gap:28px;grid-template-columns: 1fr;
}
@media (min-width:1024px){
  .grid{grid-template-columns: minmax(0,1fr) 360px;}
}

/* Hero */
.kicker{font-size:20px;font-weight:900;color:var(--ink);margin:10px 0 8px;}
h1{margin:4px 0 10px;font-size:28px;font-weight:800;color:var(--ink);}
@media (min-width:1024px){ h1{font-size:36px;} }

/* Meta boxes (الجامعة/التخصص/الجنسية) */
.meta{display:grid;gap:10px;grid-template-columns:1fr;margin:14px 0 14px;}
@media (min-width:640px){ .meta{grid-template-columns:repeat(3,1fr);} }
.meta-box{
  background:#fff;border:1px solid var(--muted);
  border-radius:10px;padding:10px 12px;color:#334155;font-size:14px;
}

/* hint */
.hint{display:flex;align-items:center;gap:8px;color:#475569;font-weight:700;margin:8px 0 14px;}

/* fields */
.fields{display:flex;flex-direction:column;gap:8px;margin-bottom:16px}
.chip{
  background:var(--field);border:1px solid var(--border);
  border-radius:10px;padding:12px 14px;color:#1f2937;font-size:16px;
}

/* Upload + CTA */
.cta-inline{display:flex;flex-direction:column;gap:10px;align-items:flex-start;margin-top:6px}
.attach{
  display:inline-flex;align-items:center;gap:8px;
  background:#e7f1ef;border:1px dashed var(--accent);
  color:#0b3b36;padding:10px 12px;border-radius:10px;font-weight:700;
}
.cta{
  display:inline-flex;align-items:center;justify-content:center;
  padding:14px 18px;border-radius:12px;background:var(--accent);
  color:var(--accent-ink);font-weight:800;border:none;box-shadow:var(--shadow);
  cursor:pointer;transition:.2s transform;
}
.cta:active{transform:translateY(1px)}

/* Sidebar Card */
.side{
  background:var(--card);color:#e5ecff;border-radius:16px;padding:18px;
  box-shadow:var(--shadow);position:relative;
}
.side h3{margin:0 0 12px;font-size:18px;color:#fff}
.side .row{display:flex;gap:10px;align-items:center;margin:10px 0}
.preset{
  width:100%;padding:10px 12px;border-radius:10px;border:1px solid #334a86;
  background:#14264a;color:#dbe4ff;font-weight:700;
}
.reset{
  width:100%;padding:10px 12px;border-radius:10px;border:1px solid #3d5aa6;
  background:#11305e;color:#fff;font-weight:800;cursor:pointer;
}

/* Format pills */
.format-toggle{
  display:grid;grid-template-columns:repeat(3,1fr);gap:8px;width:100%;
}
.pill{
  text-align:center;padding:10px 0;border-radius:10px;border:1px solid #3b4f85;
  background:#0f2144;color:#e5ecff;font-weight:800;cursor:pointer;user-select:none;
}
.pill.active{background:#25407a;}
/* Streamlit default paddings adjustments */
.block-container{padding-top: 0;}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ===== Header (HTML to control precise layout) =====
logo_path = "logo.svg"  # <-- بدّلي المسار/الاسم حسب ملفك
header_html = f"""
<div class="rtl-wrap">
  <header class="site-header">
    <div class="brand">
      <img src="{logo_path}" alt="شعار صفوة" class="header-logo" />
      <div class="brand-title">صفوة لفرز السير الذاتيه</div>
    </div>
  </header>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# ===== Main Grid (Content + "Right" Sidebar) =====
# نستخدم أعمدة ستريملت، لكن نحافظ على الستايل الداخلي مثل التصميم
col_main, col_side = st.columns([1, 0.34], gap="large")

with col_main:
    st.markdown('<div class="rtl-wrap">', unsafe_allow_html=True)

    st.markdown('<div class="kicker">فرز السير الذاتية بشكل آلي</div>', unsafe_allow_html=True)
    st.markdown('<h1 style="display:none"></h1>', unsafe_allow_html=True)  # للحفاظ على التسلسل البصري فقط

    # ثلاث بوكسات للوصف
    meta_html = """
    <div class="meta">
      <div class="meta-box">الجامعة</div>
      <div class="meta-box">التخصص</div>
      <div class="meta-box">الجنسية</div>
    </div>
    """
    st.markdown(meta_html, unsafe_allow_html=True)

    # الشرط
    st.markdown('<div class="hint">الشرط البحثي واحد او اكثر</div>', unsafe_allow_html=True)

    # الحقول
    st.session_state.uni = st.text_input("الجامعة", value=st.session_state.uni, placeholder="مثال: King Saud University", label_visibility="collapsed")
    st.session_state.nation = st.text_input("الجنسية", value=st.session_state.nation, placeholder="مثال: سعودية", label_visibility="collapsed")
    st.session_state.major = st.text_input("التخصص", value=st.session_state.major, placeholder="مثال: نظم المعلومات الإدارية", label_visibility="collapsed")
    st.session_state.extra = st.text_input("جملة شرطية إضافية…", value=st.session_state.extra, placeholder="جملة شرطية…", label_visibility="collapsed")

    # المرفقات + CTA
    st.markdown('<div class="attach">إرفاق ملفات CV (PDF)</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader("ارفع ملفات PDF", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")
    if uploaded_files:
        st.session_state.uploaded_files = uploaded_files

    # CTA
    start = st.button("ابدأ الفرز الآن", type="primary")
    if start:
        # هنا لاحقًا تربطين بخوارزمية الفرز الفعلية
        st.success("تم استقبال المدخلات والملفات. جاهزين لتطبيق خوارزمية الفرز ✅")

    st.markdown('</div>', unsafe_allow_html=True)

with col_side:
    # سايدبار ككارد داكن
    st.markdown('<div class="rtl-wrap"><div class="side">', unsafe_allow_html=True)
    st.markdown('<h3>الإعدادات</h3>', unsafe_allow_html=True)

    # Preset
    st.session_state.preset = st.selectbox("Preset", ["Preset (KSU + MIS)", "KSU Only", "MIS Only"], index=0, label_visibility="collapsed")

    # Reset
    if st.button("Reset"):
        do_reset()
        st.info("تمت إعادة التصفير.")

    # Format toggles (XLSX / PDF / CSV)
    st.markdown('<div class="row">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        xlsx_active = "active" if st.session_state.format_active == "XLSX" else ""
        if st.button("XLSX"):
            set_active("XLSX")
        st.markdown(f'<div class="pill {xlsx_active}">XLSX</div>', unsafe_allow_html=True)
    with c2:
        pdf_active = "active" if st.session_state.format_active == "PDF" else ""
        if st.button("PDF"):
            set_active("PDF")
        st.markdown(f'<div class="pill {pdf_active}">PDF</div>', unsafe_allow_html=True)
    with c3:
        csv_active = "active" if st.session_state.format_active == "CSV" else ""
        if st.button("CSV"):
            set_active("CSV")
        st.markdown(f'<div class="pill {csv_active}">CSV</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div></div>', unsafe_allow_html=True)

# ===== Notes =====
# كل المقاسات، الألوان، الخطوط مطابقة للهويّة اللي اتفقنا عليها.
# وقت ما تعطيني ملف الخط الرسمي (TTF/OTF)، أضيف @font-face مع نفس القيم ولن يتغير القياس.
