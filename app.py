# app.py
import streamlit as st
import base64
from pathlib import Path

# ============ PAGE CONFIG ============
st.set_page_config(page_title="صفوة لفرز السير الذاتيه", page_icon="🗂️", layout="wide")

# ============ SESSION STATE ============
defaults = {
    "format_active": "PDF",                      # الصيغة الافتراضية
    "preset": "Preset (KSU + MIS)",
    "uni": "King Saud University",
    "nation": "سعودية",
    "major": "نظم المعلومات الإدارية، علوم حاسب…",
    "extra": "",
    "uploaded_files": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def do_reset():
    for k, v in defaults.items():
        st.session_state[k] = v

# ============ HELPERS ============
def embed_image_as_data_uri():
    """يحاول قراءة logo.svg ثم png ثم jpg ويحوّلها Base64 كـ data URI"""
    for name in ("logo.svg", "logo.png", "logo.jpg", "logo.jpeg"):
        p = Path(name)
        if p.exists():
            data = p.read_bytes()
            ext = p.suffix.lower().lstrip(".")
            mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
            b64 = base64.b64encode(data).decode()
            return f"data:{mime};base64,{b64}"
    return ""  # ما لقينا شعار

# ============ THEME / CSS ============
st.markdown("""
<style>
/* أجبر الواجهة على الفاتح + خلفية كريمية مريحة */
html, body, [data-testid="stAppViewContainer"], .block-container {
  background: #FAFAF7 !important;  /* أبيض كريمي */
  color: #182A4E !important;
}
[data-testid="stHeader"] { background: #FAFAF7 !important; }

/* مساحة علويّة تمنع القص */
[data-testid="stAppViewContainer"] > .main, .block-container { padding-top: 14px !important; }

/* ألوان وهوية */
:root{
  --bg:#FAFAF7;   /* كريمي */
  --ink:#182A4E;  /* كحلي غامق */
  --muted:#BEC1C4;
  --field:#FFFFFF;     /* خلفية الحقول والبوكسات: أبيض واضح فوق الكريمي */
  --field-border:#E0E0E0;
  --accent:#3B7C74;    /* أخضر الأزرار */
  --accent-ink:#FFFFFF;
  --card:#182A4E;      /* كحلي السايدبار */
  --border:#E5E7EB;
  --radius:12px;
  --shadow:0 6px 20px rgba(0,0,0,.08);
}

.rtl-wrap{
  direction: rtl;
  font-family: system-ui,-apple-system,"Segoe UI","Noto Sans Arabic","Cairo","Tahoma",sans-serif;
  color: var(--ink);
}

/* ===== Header ===== */
.site-header{
  display:flex;align-items:center;justify-content:space-between;
  padding:16px 8px 12px;border-bottom:1px solid var(--border);
}
.brand{ display:flex;align-items:center;gap:12px;flex-direction:row-reverse; } /* اللوقو يمين */
.header-logo{ height:35px;width:auto;object-fit:contain; }
.brand-title{ font-weight:800;font-size:20px;color:var(--ink); }
@media (min-width:1024px){ .header-logo{height:50px} .brand-title{font-size:22px} }

/* ===== Layout ===== */
.grid{ display:grid; gap:28px; grid-template-columns:1fr; max-width:1200px; margin:0 auto; }
@media (min-width:1024px){ .grid{ grid-template-columns:minmax(0,1fr) 360px; } }

/* ===== Hero ===== */
.kicker{ font-size:20px; font-weight:900; color:var(--ink); margin:10px 0 8px; }
h1{ margin:4px 0 10px; font-size:28px; font-weight:800; color:var(--ink); }
@media (min-width:1024px){ h1{ font-size:36px; } }

/* ===== Meta boxes (الجامعة/التخصص/الجنسية) ===== */
.meta{ display:grid; gap:10px; grid-template-columns:1fr; margin:14px 0 14px; }
@media (min-width:640px){ .meta{ grid-template-columns:repeat(3,1fr); } }
.meta-box{
  background: var(--field);
  border: 1px solid var(--field-border);
  border-radius:10px; padding:10px 12px; color:#334155; font-size:14px;
}

/* hint */
.hint{ display:flex; align-items:center; gap:8px; color:#475569; font-weight:700; margin:8px 0 14px; }

/* ===== Inputs look (تشبه البوكسات بالضبط) ===== */
.stTextInput > div > div input{
  background: var(--field) !important;
  border: 1px solid var(--field-border) !important;
  border-radius: 10px !important;
  color:#1f2937 !important;
}
.stTextInput > div > div{ border-radius:10px !important; }

/* ===== Upload + CTA ===== */
.cta-inline{ display:flex; flex-direction:column; gap:10px; align-items:flex-start; margin-top:6px }
.attach{
  display:inline-flex; align-items:center; gap:8px;
  background:#E7F1EF; border:1px dashed var(--accent);
  color:#0b3b36; padding:10px 12px; border-radius:10px; font-weight:700;
}
.cta{
  display:inline-flex; align-items:center; justify-content:center;
  padding:14px 18px; border-radius:12px; background:var(--accent);
  color:var(--accent-ink); font-weight:800; border:none; box-shadow:var(--shadow);
  cursor:pointer; transition:.2s transform;
}
.cta:active{ transform:translateY(1px) }

/* ===== Sidebar (بوكس كحلي) ===== */
.side{
  background: var(--card); color:#FFFFFF; border-radius:16px; padding:18px; box-shadow:var(--shadow);
}
.side h3{ margin:0 0 12px; font-size:18px; font-weight:800; color:#FFFFFF; }

/* Badge علوي صغير لو احتجناه */
.badge{
  display:inline-block; background:#0f2144; color:#fff; padding:6px 10px; border-radius:10px; font-weight:800; font-size:12px;
}

/* Reset + Preset */
.preset{
  width:100%; padding:10px 12px; border-radius:10px;
  border:1px solid #334a86; background:#14264a; color:#dbe4ff; font-weight:700;
}
.reset-btn button{
  width:100% !important; padding:10px 12px !important; border-radius:10px !important;
  border:1px solid #3d5aa6 !important; background:#11305e !important; color:#fff !important; font-weight:800 !important;
}

/* ===== Radio Pills (XLSX / PDF / CSV) ===== */
.stRadio > div{ display:flex; gap:8px; justify-content:space-between; }
.stRadio label{
  flex:1; text-align:center; padding:10px 0; border-radius:10px;
  border:1px solid #3b4f85; background:#0f2144; color:#e5ecff; font-weight:800; cursor:pointer;
}
/* حالة مفعلة */
.stRadio input:checked + div > p{ color:#fff !important; }
.stRadio [data-baseweb="radio"] input:checked ~ div{
  background:#25407a !important; border-color:#25407a !important;
}

/* فواصل ناعمة */
hr.sep{ border:none; border-top:1px solid rgba(255,255,255,.15); margin:10px 0 0; }
</style>
""", unsafe_allow_html=True)

# ============ HEADER ============
logo_data_uri = embed_image_as_data_uri()
header_html = f"""
<div class="rtl-wrap">
  <header class="site-header">
    <div class="brand">
      {f'<img src="{logo_data_uri}" alt="شعار صفوة" class="header-logo" />' if logo_data_uri else ''}
      <div class="brand-title">صفوة لفرز السير الذاتيه</div>
    </div>
  </header>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)
if not logo_data_uri:
    st.warning("تنبيه: لم يتم العثور على ملف الشعار (logo.svg/png/jpg) في نفس مجلد التطبيق.")

# ============ LAYOUT ============
st.markdown('<div class="grid rtl-wrap">', unsafe_allow_html=True)
col_main, col_side = st.columns([1, 0.34], gap="large")

with col_main:
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

    # الحقول (مطابقة شكل البوكسات)
    st.session_state.uni = st.text_input("الجامعة", value=st.session_state.uni, placeholder="مثال: King Saud University", label_visibility="collapsed")
    st.session_state.nation = st.text_input("الجنسية", value=st.session_state.nation, placeholder="مثال: سعودية", label_visibility="collapsed")
    st.session_state.major = st.text_input("التخصص", value=st.session_state.major, placeholder="مثال: نظم المعلومات الإدارية", label_visibility="collapsed")
    st.session_state.extra = st.text_input("جملة شرطية إضافية…", value=st.session_state.extra, placeholder="جملة شرطية…", label_visibility="collapsed")

    # المرفقات + CTA — ديناميكي حسب الصيغة
    ext_map = {"PDF": ["pdf"], "XLSX": ["xlsx"], "CSV": ["csv"]}
    label = f"إرفاق ملفات CV ({st.session_state.format_active})"
    st.markdown(f'<div class="cta-inline"><div class="attach">{label}</div>', unsafe_allow_html=True)
    st.session_state.uploaded_files = st.file_uploader(
        "Upload files",
        type=ext_map.get(st.session_state.format_active, ["pdf"]),
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    start = st.button("ابدأ الفرز الآن", type="primary")
    st.markdown('</div>', unsafe_allow_html=True)  # close cta-inline

    if start:
        st.success("تم استقبال المدخلات والملفات. جاهزين لتطبيق خوارزمية الفرز ✅")

with col_side:
    st.markdown('<div class="side">', unsafe_allow_html=True)
    st.markdown('<h3>الإعدادات</h3>', unsafe_allow_html=True)

    # Preset
    st.session_state.preset = st.selectbox(
        "Preset", ["Preset (KSU + MIS)", "KSU Only", "MIS Only"],
        index=0, label_visibility="collapsed"
    )

    # مراجعة اختيارات المستخدم
    st.markdown("<hr class='sep'/>", unsafe_allow_html=True)
    st.markdown("**اختياراتك الحالية:**")
    st.write(f"📌 الجامعة: {st.session_state.uni or '—'}")
    st.write(f"📌 الجنسية: {st.session_state.nation or '—'}")
    st.write(f"📌 التخصص: {st.session_state.major or '—'}")
    if st.session_state.extra:
        st.write(f"📌 شرط إضافي: {st.session_state.extra}")

    # Reset
    with st.container():
        st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
        if st.button("Reset"):
            do_reset()
            st.info("تمت إعادة التصفير.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Radio Pills: ثلاث خيارات فقط
    st.radio(
        "format",
        ["XLSX", "PDF", "CSV"],
        index=["XLSX","PDF","CSV"].index(st.session_state.format_active) if st.session_state.format_active in ["XLSX","PDF","CSV"] else 1,
        horizontal=True,
        label_visibility="collapsed",
        key="format_active"
    )

    st.markdown('</div>', unsafe_allow_html=True)  # close .side

st.markdown('</div>', unsafe_allow_html=True)  # close .grid
