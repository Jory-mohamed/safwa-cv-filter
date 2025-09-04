# app.py
import streamlit as st
import base64
from pathlib import Path

# ================== PAGE CONFIG ==================
st.set_page_config(
    page_title="صفوة لفرز السير الذاتيه",
    page_icon="🗂️",
    layout="wide"
)

# ================== SESSION STATE ==================
if "format_active" not in st.session_state:
    st.session_state.format_active = "PDF"   # الافتراضي
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
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = None

def set_active(fmt: str):
    st.session_state.format_active = fmt

def do_reset():
    st.session_state.format_active = "PDF"
    st.session_state.preset = "Preset (KSU + MIS)"
    st.session_state.uni = ""
    st.session_state.nation = ""
    st.session_state.major = ""
    st.session_state.extra = ""
    st.session_state.uploaded_files = None

# ================== GLOBAL CSS ==================
st.markdown("""
<style>
/* إجبار واجهة فاتحة مهما كان نظام المستخدم */
html, body, [data-testid="stAppViewContainer"], .block-container { background: #FFFFFF !important; color: #182A4E !important; }
[data-testid="stHeader"] { background: #FFFFFF !important; }

/* مساحة علويّة تمنع القصّ */
[data-testid="stAppViewContainer"] > .main { padding-top: 12px !important; }
.block-container { padding-top: 12px !important; }

/* ألوان وهوية */
:root{
  --bg:#FFFFFF;
  --ink:#182A4E;        /* كحلي العناوين */
  --muted:#BEC1C4;      /* الرمادي المتفق عليه */
  --field:#F3F4F5;      /* خلفية الحقول */
  --accent:#3B7C74;     /* الأخضر للأزرار */
  --accent-ink:#FFFFFF;
  --card:#0f1f3d;       /* الكارد الداكن */
  --border:#E5E7EB;
  --radius:12px;
  --shadow:0 6px 20px rgba(0,0,0,.06);
}

.rtl-wrap { direction: rtl; font-family: system-ui,-apple-system,"Segoe UI","Noto Sans Arabic","Cairo","Tahoma",sans-serif; color: var(--ink); }

/* Header */
.site-header{
  display:flex;align-items:center;justify-content:space-between;
  padding:16px 8px 12px;border-bottom:1px solid var(--border);
}
.brand{ display:flex;align-items:center;gap:12px; flex-direction:row-reverse; } /* اللوقو يمين */
.header-logo{ height:35px;width:auto;object-fit:contain; }
.brand-title{ font-weight:800;font-size:20px;letter-spacing:.2px;color:var(--ink); }
@media (min-width:1024px){
  .header-logo{ height:50px; }
  .brand-title{ font-size:22px; }
}

/* Layout */
.grid{ display:grid; gap:28px; grid-template-columns: 1fr; max-width:1200px; margin:0 auto; }
@media (min-width:1024px){ .grid{ grid-template-columns: minmax(0,1fr) 360px; } }

/* Hero */
.kicker{font-size:20px;font-weight:900;color:var(--ink);margin:10px 0 8px;}
h1{margin:4px 0 10px;font-size:28px;font-weight:800;color:var(--ink);}
@media (min-width:1024px){ h1{font-size:36px;} }

/* Meta boxes */
.meta{display:grid;gap:10px;grid-template-columns:1fr;margin:14px 0 14px;}
@media (min-width:640px){ .meta{grid-template-columns:repeat(3,1fr);} }
.meta-box{ background:#fff;border:1px solid var(--muted); border-radius:10px; padding:10px 12px; color:#334155; font-size:14px; }

/* hint */
.hint{display:flex;align-items:center;gap:8px;color:#475569;font-weight:700;margin:8px 0 14px;}

/* Inputs look */
.stTextInput > div > div input { background: var(--field); border: 1px solid var(--border); border-radius: 10px; color: #1f2937; }
.stTextInput > div > div { border-radius:10px; }

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

/* Sidebar */
.side{ background:var(--card); color:#e5ecff; border-radius:16px; padding:18px; box-shadow:var(--shadow); position:relative; }
.side h3{ margin:0 0 12px; font-size:18px; color:#fff; }
.side .row{ display:flex; gap:10px; align-items:center; margin:10px 0; }
.preset{ width:100%; padding:10px 12px; border-radius:10px; border:1px solid #334a86; background:#14264a; color:#dbe4ff; font-weight:700; }
.reset{ width:100%; padding:10px 12px; border-radius:10px; border:1px solid #3d5aa6; background:#11305e; color:#fff; font-weight:800; cursor:pointer; }

/* Format pills */
.format-toggle{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; width:100%; }
.pill{ text-align:center; padding:10px 0; border-radius:10px; border:1px solid #3b4f85; background:#0f2144; color:#e5ecff; font-weight:800; user-select:none; }
.pill.active{ background:#25407a; }

/* little helper */
hr.sep{ border:none; border-top:1px solid rgba(255,255,255,.15); margin:10px 0 0; }
</style>
""", unsafe_allow_html=True)

# ================== LOGO (BASE64 EMBED) ==================
def embed_image_as_data_uri(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    data = p.read_bytes()
    ext = p.suffix.lower().lstrip(".")
    mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
    b64 = base64.b64encode(data).decode()
    return f"data:{mime};base64,{b64}"

logo_path = "logo.svg"  # عدّلي الاسم إذا كان مختلف
logo_src = embed_image_as_data_uri(logo_path)

# ================== HEADER ==================
header_html = f"""
<div class="rtl-wrap">
  <header class="site-header">
    <div class="brand">
      {('<img src="'+logo_src+'" alt="شعار صفوة" class="header-logo" />') if logo_src else ''}
      <div class="brand-title">صفوة لفرز السير الذاتيه</div>
    </div>
  </header>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# ================== LAYOUT (MAIN + SIDEBAR) ==================
st.markdown('<div class="grid rtl-wrap">', unsafe_allow_html=True)
col_main, col_side = st.columns([1, 0.34], gap="large")

with col_main:
    st.markdown('<div>', unsafe_allow_html=True)

    # العنوان + هيرو
    st.markdown('<div class="kicker">فرز السير الذاتية بشكل آلي</div>', unsafe_allow_html=True)
    st.markdown('<h1 style="display:none"></h1>', unsafe_allow_html=True)

    # ثلاث بوكسات للوصف
    st.markdown("""
    <div class="meta">
      <div class="meta-box">الجامعة</div>
      <div class="meta-box">التخصص</div>
      <div class="meta-box">الجنسية</div>
    </div>
    """, unsafe_allow_html=True)

    # الشرط
    st.markdown('<div class="hint">الشرط البحثي واحد او اكثر</div>', unsafe_allow_html=True)

    # الحقول
    st.session_state.uni = st.text_input("الجامعة", value=st.session_state.uni, placeholder="مثال: King Saud University", label_visibility="collapsed")
    st.session_state.nation = st.text_input("الجنسية", value=st.session_state.nation, placeholder="مثال: سعودية", label_visibility="collapsed")
    st.session_state.major = st.text_input("التخصص", value=st.session_state.major, placeholder="مثال: نظم المعلومات الإدارية", label_visibility="collapsed")
    st.session_state.extra = st.text_input("جملة شرطية إضافية…", value=st.session_state.extra, placeholder="جملة شرطية…", label_visibility="collapsed")

    # المرفقات + CTA — ديناميكي حسب الصيغة المختارة
    file_label = f"إرفاق ملفات CV ({st.session_state.format_active})"
    st.markdown(f'<div class="cta-inline"><div class="attach">{file_label}</div>', unsafe_allow_html=True)

    ext_map = {"PDF": ["pdf"], "XLSX": ["xlsx"], "CSV": ["csv"]}
    st.session_state.uploaded_files = st.file_uploader(
        "Upload files",
        type=ext_map.get(st.session_state.format_active, ["pdf"]),
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    # زر ابدأ
    start = st.button("ابدأ الفرز الآن", type="primary")
    st.markdown('</div>', unsafe_allow_html=True)  # close cta-inline

    if start:
        st.success("تم استقبال المدخلات والملفات. جاهزين لتطبيق خوارزمية الفرز ✅")

    st.markdown('</div>', unsafe_allow_html=True)

with col_side:
    st.markdown('<div class="side">', unsafe_allow_html=True)
    st.markdown('<h3>الإعدادات</h3>', unsafe_allow_html=True)

    # Preset (يبقى موجود) + مراجعة اختيارات المستخدم بشكل حي
    st.session_state.preset = st.selectbox("Preset", ["Preset (KSU + MIS)", "KSU Only", "MIS Only"], index=0, label_visibility="collapsed")

    # مراجعة اختيارات المستخدم (جامعة/تخصص/جنسية/شرط)
    st.markdown("<hr class='sep'/>", unsafe_allow_html=True)
    st.markdown("**اختياراتك الحالية:**")
    st.write(f"📌 الجامعة: {st.session_state.uni or '—'}")
    st.write(f"📌 الجنسية: {st.session_state.nation or '—'}")
    st.write(f"📌 التخصص: {st.session_state.major or '—'}")
    if st.session_state.extra:
        st.write(f"📌 شرط إضافي: {st.session_state.extra}")

    # Reset
    if st.button("Reset"):
        do_reset()
        st.info("تمت إعادة التصفير.")

    # Format toggles (XLSX / PDF / CSV) — تفعيل فعلي وتلوين حسب النشط
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("XLSX"):
            set_active("XLSX")
        st.markdown(f"<div class='pill {'active' if st.session_state.format_active=='XLSX' else ''}'>XLSX</div>", unsafe_allow_html=True)
    with c2:
        if st.button("PDF"):
            set_active("PDF")
        st.markdown(f"<div class='pill {'active' if st.session_state.format_active=='PDF' else ''}'>PDF</div>", unsafe_allow_html=True)
    with c3:
        if st.button("CSV"):
            set_active("CSV")
        st.markdown(f"<div class='pill {'active' if st.session_state.format_active=='CSV' else ''}'>CSV</div>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # close .side

st.markdown('</div>', unsafe_allow_html=True)  # close .grid
