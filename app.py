# app.py
import streamlit as st, base64
from pathlib import Path

# ---------- Page ----------
st.set_page_config(page_title="صفوة لفرز السير الذاتيه", page_icon="🗂️", layout="wide")

# ---------- Session State ----------
st.session_state.setdefault("format_active", "PDF")
st.session_state.setdefault("uni", "King Saud University")
st.session_state.setdefault("nation", "سعودية")
st.session_state.setdefault("major", "نظم المعلومات الإدارية، علوم حاسب…")
st.session_state.setdefault("extra", "")
st.session_state.setdefault("preset", "Preset (KSU + MIS)")
st.session_state.setdefault("uploaded_files", None)

def do_reset():
    st.session_state.update({
        "format_active":"PDF","uni":"","nation":"","major":"","extra":"",
        "preset":"Preset (KSU + MIS)","uploaded_files":None
    })

# ---------- Logo Helper ----------
def logo_data_uri():
    for name in ("logo.svg","logo.png","logo.jpg","logo.jpeg"):
        p=Path(name)
        if p.exists():
            b=p.read_bytes(); ext=p.suffix.lower().lstrip(".")
            mime="image/svg+xml" if ext=="svg" else f"image/{ext}"
            return f"data:{mime};base64,{base64.b64encode(b).decode()}"
    return ""

# ---------- CSS ----------
st.markdown("""
<style>
/* خلفية كريمية + نص كحلي */
html,body,[data-testid="stAppViewContainer"],.block-container{
  background:#f5f5e6!important; color:#182A4E!important
}
[data-testid="stHeader"]{background:#f5f5e6!important}
[data-testid="stAppViewContainer"]>.main,.block-container{padding-top:14px!important}

/* هوية */
:root{
  --ink:#182A4E; --muted:#BEC1C4; --field:#FFFFFF; --field-b:#E0E0E0;
  --accent:#3B7C74; --card:#182A4E; --shadow:0 6px 20px rgba(0,0,0,.08);
}

/* Header */
.rtl{direction:rtl;font-family:system-ui,-apple-system,"Noto Sans Arabic","Cairo","Segoe UI",Tahoma,sans-serif}
.site-header{display:flex;align-items:center;gap:12px;border-bottom:1px solid #E5E7EB;padding:10px 8px 12px}
.header-logo{height:35px;width:auto;object-fit:contain}
.brand-title{font-weight:800;font-size:20px;color:var(--ink)}
@media (min-width:1024px){.header-logo{height:50px}.brand-title{font-size:22px}}

/* Layout */
.grid{display:grid;gap:28px;grid-template-columns:1fr;max-width:1200px;margin:0 auto}
@media (min-width:1024px){.grid{grid-template-columns:minmax(0,1fr) 360px}}

/* Hero */
.kicker{font-size:20px;font-weight:900;color:var(--ink);margin:8px 0}
h1{margin:0 0 8px;font-size:28px;font-weight:800;color:var(--ink)}
@media (min-width:1024px){h1{font-size:36px}}

/* Meta boxes */
.meta{display:grid;gap:10px;grid-template-columns:1fr;margin:12px 0}
@media (min-width:640px){.meta{grid-template-columns:repeat(3,1fr)}}
.meta-box{background:var(--field);border:1px solid var(--field-b);border-radius:10px;padding:10px 12px;color:#334155;font-size:14px}

/* hint */
.hint{color:#475569;font-weight:700;margin:6px 0 12px}

/* Inputs */
.stTextInput > div > div input{
  background:var(--field)!important;border:1px solid var(--field-b)!important;
  border-radius:10px!important;color:#1f2937!important
}
.stTextInput > div > div{border-radius:10px!important}

/* Upload + CTA */
.cta-box{display:flex;flex-direction:column;gap:10px;align-items:flex-start;margin-top:6px}
.attach{display:inline-flex;align-items:center;gap:8px;background:#E7F1EF;border:1px dashed var(--accent);color:#0b3b36;padding:10px 12px;border-radius:10px;font-weight:700}
.stFileUploader>div>div{border-radius:12px}

/* Sidebar (بوكس كحلي) */
div[data-testid="column"]:nth-of-type(2) > div {
  background: var(--card); border-radius:16px; padding:18px; box-shadow:var(--shadow);
}
div[data-testid="column"]:nth-of-type(2) *{color:#e9f0ff}
div[data-testid="column"]:nth-of-type(2) h3{color:#fff!important;margin:0 0 10px;font-size:20px;font-weight:800}

/* Preset */
div[data-testid="column"]:nth-of-type(2) .stSelectbox > div{background:#14264a;border:1px solid #334a86;border-radius:10px}
div[data-testid="column"]:nth-of-type(2) .stSelectbox svg{filter:invert(1)}

/* Reset */
div[data-testid="column"]:nth-of-type(2) .reset-btn button{
  width:100%!important;padding:10px 12px!important;border-radius:10px!important;
  border:1px solid #3d5aa6!important;background:#11305e!important;color:#fff!important;font-weight:800!important
}

/* كبسولات XLSX/PDF/CSV */
div[data-testid="column"]:nth-of-type(2) .stRadio > div{display:flex;gap:8px;justify-content:space-between}
div[data-testid="column"]:nth-of-type(2) .stRadio label{
  flex:1;text-align:center;padding:10px 0;border-radius:10px;border:1px solid #3b4f85;
  background:#0f2144;color:#e5ecff;font-weight:800;cursor:pointer
}
div[data-testid="column"]:nth-of-type(2) .stRadio input:checked + div{
  background:#25407a!important;border-color:#25407a!important
}
</style>
""", unsafe_allow_html=True)

# ---------- Header ----------
logo_uri = logo_data_uri()
st.markdown(
    f"""
    <div class="rtl">
      <div class="site-header" style="justify-content:flex-end">
        {'<img src="'+logo_uri+'" class="header-logo" alt="Logo"/>' if logo_uri else ''}
        <div class="brand-title">صفوة لفرز السير الذاتيه</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)
if not logo_uri:
    st.warning("تنبيه: ملف الشعار غير موجود (logo.svg/png/jpg) في نفس مجلد التطبيق.", icon="⚠️")

# ---------- Layout ----------
st.markdown('<div class="grid rtl">', unsafe_allow_html=True)
col_main, col_side = st.columns([1, 0.34], gap="large")

with col_main:
    st.markdown('<div class="kicker">فرز السير الذاتية بشكل آلي</div>', unsafe_allow_html=True)
    st.markdown('<h1 style="display:none"></h1>', unsafe_allow_html=True)

    st.markdown("""
    <div class="meta">
      <div class="meta-box">الجامعة</div>
      <div class="meta-box">التخصص</div>
      <div class="meta-box">الجنسية</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="hint">الشرط البحثي واحد او اكثر</div>', unsafe_allow_html=True)

    st.session_state.uni    = st.text_input("الجامعة", value=st.session_state.uni,   placeholder="مثال: King Saud University", label_visibility="collapsed")
    st.session_state.nation = st.text_input("الجنسية", value=st.session_state.nation, placeholder="مثال: سعودية",                label_visibility="collapsed")
    st.session_state.major  = st.text_input("التخصص",  value=st.session_state.major,  placeholder="مثال: نظم المعلومات الإدارية", label_visibility="collapsed")
    st.session_state.extra  = st.text_input("شرط إضافي", value=st.session_state.extra, placeholder="جملة شرطية…", label_visibility="collapsed")

    # المرفقات + CTA (ديناميكي)
    ext_map = {"PDF":["pdf"], "XLSX":["xlsx"], "CSV":["csv"]}
    label = f"إرفاق ملفات CV ({st.session_state.get('format_active','PDF')})"
    st.markdown(f'<div class="cta-box"><div class="attach">{label}</div>', unsafe_allow_html=True)
    st.session_state.uploaded_files = st.file_uploader("Upload", type=ext_map[st.session_state.get("format_active","PDF")], accept_multiple_files=True, label_visibility="collapsed")
    st.button("ابدأ الفرز الآن", type="primary")
    st.markdown('</div>', unsafe_allow_html=True)  # close cta-box

with col_side:
    st.markdown("### الإعدادات")
    st.session_state.preset = st.selectbox("Preset", ["Preset (KSU + MIS)", "KSU Only", "MIS Only"], index=0, label_visibility="collapsed")

    st.markdown("**اختياراتك الحالية:**")
    st.write(f"📌 الجامعة: {st.session_state.uni or '—'}")
    st.write(f"📌 الجنسية: {st.session_state.nation or '—'}")
    st.write(f"📌 التخصص: {st.session_state.major or '—'}")
    if st.session_state.extra: st.write(f"📌 شرط إضافي: {st.session_state.extra}")

    # Reset
    st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
    if st.button("Reset"):
        do_reset(); st.info("تمت إعادة التصفير.")
    st.markdown('</div>', unsafe_allow_html=True)

    # كبسولات 3 فقط
    choice = st.radio("format", ["XLSX","PDF","CSV"],
                      index=["XLSX","PDF","CSV"].index(st.session_state.get("format_active","PDF")),
                      horizontal=True, label_visibility="collapsed")
    st.session_state.format_active = choice

st.markdown("</div>", unsafe_allow_html=True)  # /grid
