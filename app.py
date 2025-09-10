# app.py
# — تطبيق CV Filter خفيف، يعمل مباشرة على Streamlit بدون تبعيات خارجية —
# ملاحظات:
# - ما يحتاج مكتبات استخراج PDF/Docx (تجنّباً للأخطاء). نعتمد تحليل بسيط بالاسم/النص المرفوع.
# - عرض الملفات بالعرض (كروت أفقية).
# - ألوان هادئة وواضحة (بدون أسود ولا أخضر فاقع).
# - تحكّم فوري بحجم اللوقو من الشريط الجانبي.

import streamlit as st
import io

# -------------------------
# الإعدادات العامة و الثيم
# -------------------------
st.set_page_config(
    page_title="Safwa CV Filter",
    page_icon="🧾",
    layout="wide",
)

# لوحة ألوان لطيفة (بدون أسود/أخضر فاقع)
PRIMARY = "#3A6EA5"   # أزرق هادئ
ACCENT  = "#E0AFA0"   # وردي ترابي
BG      = "#F7F7FB"   # خلفية فاتحة جدًا
CARD    = "#FFFFFF"   # خلفية الكروت
TEXT    = "#1F2937"   # رمادي غامق مقروء
MUTED   = "#6B7280"   # رمادي للنصوص الثانوية
SUCCESS = "#2E7D32"   # أخضر داكن هادئ للتفوق/القبول
WARN    = "#B45309"   # برتقالي تنبيه
FAIL    = "#9B1C1C"   # أحمر هاديء للرفض

# حقن CSS للتصميم
st.markdown(
    f"""
    <style>
    .stApp {{
        background: {BG};
        color: {TEXT};
        font-family: "Inter", system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    }}
    /* أزرار */
    .stButton>button {{
        border-radius: 10px;
        font-weight: 600;
        border: 1px solid rgba(0,0,0,0.06);
    }}
    .stButton>button[kind="primary"] {{
        background: {PRIMARY};
        color: white;
    }}
    /* مدخلات */
    .stTextInput>div>div>input,
    .stTextArea textarea,
    .stSelectbox>div>div>div>div,
    .stFileUploader>div {{ 
        background: {CARD};
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 10px;
        color: {TEXT};
    }}
    /* شارة/Chip صغيرة */
    .chip {{
        display:inline-block; 
        padding: 4px 10px; 
        background:{ACCENT}22; 
        border:1px solid {ACCENT}55; 
        border-radius:999px; 
        font-size:12px; 
        margin-right:6px;
    }}
    /* كرت */
    .card {{
        background:{CARD};
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 14px;
        padding: 14px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        height: 100%;
    }}
    .card h4 {{ margin: 0 0 6px 0; }}
    .muted {{ color:{MUTED}; font-size: 13px; }}
    .ok {{ color:{SUCCESS}; font-weight:600; }}
    .warn {{ color:{WARN}; font-weight:600; }}
    .bad {{ color:{FAIL}; font-weight:600; }}
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------
# الشريط الجانبي (لوقو + إعدادات)
# -------------------------
st.sidebar.markdown("### ⚙️ الإعدادات")

logo_file = st.sidebar.file_uploader("ارفع اللوقو (اختياري)", type=["png", "jpg", "jpeg"])
logo_width = st.sidebar.slider("حجم اللوقو", min_value=60, max_value=300, value=140, step=10)

if logo_file:
    st.sidebar.image(logo_file, width=logo_width, caption="شعار التطبيق")

preset = st.sidebar.selectbox(
    "Preset (مفاتيح جاهزة)",
    options=[
        "بدون",
        "KSU + MIS",
        "Data/AI Basics",
        "Fresh Graduate"
    ],
    index=0
)

# مفتاح الكلمات حسب البريست
PRESET_KEYWORDS = {
    "بدون": [],
    "KSU + MIS": ["جامعة الملك سعود", "KSU", "MIS", "نظم المعلومات الإدارية", "كلية الإدارة"],
    "Data/AI Basics": ["Python", "SQL", "Excel", "Pandas", "Machine Learning", "Data Analysis"],
    "Fresh Graduate": ["Fresh Graduate", "حديث التخرج", "Internship", "Co-op", "تدريب تعاوني"]
}

extra_keywords = st.sidebar.text_area(
    "كلمات مفتاحية إضافية (اختياري) — افصلي بينها بفاصلة ,",
    placeholder="مثال: SDAIA, Streamlit, OCR"
)

# عتبات بسيطة لاتخاذ قرار مبدئي
min_hit_for_pass = st.sidebar.slider("الحد الأدنى لاعتبار السيرة مناسبة (Hits)", 1, 10, 2)

# -------------------------
# رأس الصفحة
# -------------------------
col_a, col_b = st.columns([0.8, 0.2])
with col_a:
    st.markdown("## 🧾 Safwa CV Filter — إصدار خفيف")
    st.markdown(
        f'<span class="chip">مرتب</span> <span class="chip">سريع</span> <span class="chip">بدون تبعيات</span>',
        unsafe_allow_html=True
    )
with col_b:
    st.markdown("")

st.write("")  # مسافة بسيطة

# -------------------------
# منطقة الرفع والتحكم
# -------------------------
uploaded_files = st.file_uploader(
    "ارفعي السير الذاتية (PDF/Docx/Text) — تقدرين تختارين أكثر من ملف",
    accept_multiple_files=True,
    type=["pdf", "docx", "txt"]
)

search_text = st.text_input(
    "جملة بحث (اختياري) — نتحقق منها داخل الملف لو توفّر نص",
    placeholder="مثال: King Saud University نظم المعلومات الإدارية Python"
)

go = st.button("ابدأ الفرز الآن ✅", type="primary", use_container_width=True)

# -------------------------
# دوال مساعدة
# -------------------------
def safe_sniff_text(file) -> str:
    """
    محاولة بسيطة لقراءة جزء من النص بدون تبعيات.
    - ملفات txt: نقراها مباشرة
    - غير ذلك: نكتفي بعرض الاسم (تجنّباً لأخطاء حزم PDF/Docx)
    """
    try:
        name = file.name.lower()
        if name.endswith(".txt"):
            # نعيد أول 10KB كأقصى حد
            raw = file.read(10_000)
            try:
                return raw.decode("utf-8", errors="ignore")
            except Exception:
                return raw.decode("latin-1", errors="ignore")
        else:
            # لا نحاول فتح PDF/Docx هنا عشان ما نفشل بدون مكتبات
            return ""
    except Exception:
        return ""

def score_file(name: str, peek_text: str, keywords: list[str]) -> dict:
    """
    نحسب Hits مبسّطة بالاعتماد على الاسم + جزء النص المقروء (لو موجود .txt).
    """
    target = (name + " " + peek_text).lower()
    hits = 0
    hit_terms = []
    for kw in keywords:
        if not kw:
            continue
        if kw.lower() in target:
            hits += 1
            hit_terms.append(kw)
    # معيار قبول مبدئي
    decision = "مناسب" if hits >= min_hit_for_pass else "يحتاج مراجعة"
    return {"hits": hits, "hit_terms": hit_terms, "decision": decision}

# تحضير قائمة الكلمات
keywords = PRESET_KEYWORDS.get(preset, []).copy()
if extra_keywords.strip():
    for piece in extra_keywords.split(","):
        kw = piece.strip()
        if kw:
            keywords.append(kw)

if search_text.strip():
    # نعتبر كل كلمة مفتاحية فردية من حقل البحث (تقريب بسيط)
    for token in search_text.split():
        if token.strip():
            keywords.append(token.strip())

# -------------------------
# عرض النتائج (كروت بالعرض)
# -------------------------
if go:
    if not uploaded_files:
        st.warning("ارفعي ملفات أولًا.")
    else:
        st.markdown("### النتائج")
        # نعرض الملفات على صفوف أفقية 3 في كل صف
        CHUNK = 3
        for i in range(0, len(uploaded_files), CHUNK):
            row = uploaded_files[i:i+CHUNK]
            cols = st.columns(len(row))
            for c, f in zip(cols, row):
                with c:
                    # قراءة نص (آمن)
                    # مهم: نرجّع مؤشر الملف للبداية بعد أي read
                    peek = safe_sniff_text(f)
                    try:
                        f.seek(0)
                    except Exception:
                        pass

                    result = score_file(f.name, peek, keywords)

                    # بطاقة
                    st.markdown(
                        f"""
                        <div class="card">
                            <h4>{f.name}</h4>
                            <div class="muted">Hits: {result['hits']} — 
                            {"<span class='ok'>مناسب</span>" if result['decision']=="مناسب" else "<span class='warn'>يحتاج مراجعة</span>"}
                            </div>
                        """,
                        unsafe_allow_html=True
                    )

                    if result["hit_terms"]:
                        st.markdown(
                            "الكلمات المطابقة: " + " • ".join([f"`{t}`" for t in result["hit_terms"]])
                        )
                    else:
                        st.markdown("<span class='muted'>لا توجد تطابقات واضحة</span>", unsafe_allow_html=True)

                    with st.expander("معاينة سريعة"):
                        if peek:
                            st.text(peek[:1000])
                        else:
                            st.caption("لا توجد معاينة نصية (ملف PDF/Docx). المعالجة النصية الكاملة غير مفعّلة في هذا الإصدار الخفيف.")

                    st.markdown("</div>", unsafe_allow_html=True)

        # ملاحظات خفيفة
        st.info(
            "هذا إصدار خفيف بدون استخراج نص من PDF/Docx لتفادي مشاكل التبعيات. "
            "لو تبين إصدار احترافي باستخراج نص دقيق ودعم OCR بنفعّله لك بنسخة ثانية."
        )

# -------------------------
# تذييل
# -------------------------
st.markdown("---")
st.caption(
    f"الواجهة بألوان هادئة • بدون أسود/أخضر فاقع • تحكم بحجم اللوقو من الشريط الجانبي • العرض أفقي بالكروت."
)