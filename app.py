import streamlit as st
import pdfplumber

# ---------------- إعداد الصفحة ----------------
st.set_page_config(
    page_title="صفوة لفرز السير الذاتية",
    layout="wide"
)

st.title("صفوة لفرز السير الذاتية بشكل آلي")

# ---------------- Session Keys ----------------
UNI_KEY    = "uni_field"
MAJOR_KEY  = "major_field"
NATION_KEY = "nation_field"
EXTRA_KEY  = "extra_field"

# تأكد أن القيم الابتدائية فاضية
for k in (UNI_KEY, MAJOR_KEY, NATION_KEY, EXTRA_KEY):
    st.session_state.setdefault(k, "")

# ---------------- واجهة الإدخال ----------------
c1, c2 = st.columns(2)
with c1:
    uni = st.text_input(
        "الجامعة",
        value="",
        placeholder="مثال: جامعة الملك سعود",
        key=UNI_KEY
    )
with c2:
    major = st.text_input(
        "التخصص",
        value="",
        placeholder="مثال: نظم معلومات إدارية",
        key=MAJOR_KEY
    )

nation = st.text_input(
    "الجنسية",
    value="",
    placeholder="مثال: سعودي / Non-Saudi",
    key=NATION_KEY
)

extra = st.text_input(
    "كلمات إضافية (اختياري)",
    value="",
    placeholder="مثال: خبرة، تدريب صيفي",
    key=EXTRA_KEY
)

# زر إعادة تعيين
if st.button("إعادة تعيين"):
    for k in (UNI_KEY, MAJOR_KEY, NATION_KEY, EXTRA_KEY):
        st.session_state[k] = ""
    st.experimental_rerun()

# ---------------- رفع الملفات ----------------
uploaded_files = st.file_uploader(
    "إرفاق ملفات CV (PDF فقط حالياً)",
    type=["pdf"],
    accept_multiple_files=True
)

# ---------------- منطق الفرز ----------------
def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text.lower()

if st.button("ابدأ الفرز الآن"):
    if not uploaded_files:
        st.warning("الرجاء رفع ملف واحد على الأقل.")
    else:
        st.write("### النتائج:")
        for file in uploaded_files:
            content = extract_text_from_pdf(file)

            # تحقق من الشروط
            conditions = [
                (uni.lower() in content) if uni else True,
                (major.lower() in content) if major else True,
                (nation.lower() in content) if nation else True,
                (extra.lower() in content) if extra else True,
            ]

            if all(conditions):
                st.success(f"✅ {file.name} مطابق للشروط")
            else:
                st.error(f"❌ {file.name} غير مطابق")