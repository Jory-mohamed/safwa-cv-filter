import streamlit as st
from PyPDF2 import PdfReader

st.set_page_config(page_title="صفوة لفرز السير الذاتية", page_icon="📝", layout="centered")
st.title("✨ صفوة لفرز السير الذاتية (نسخة PDF مؤقتًا) ✨")

uni   = st.text_input("الجامعة")
major = st.text_input("التخصص")
nation= st.text_input("الجنسية")

uploaded_files = st.file_uploader(
    "✨ ارفعي ملفات PDF فقط (مؤقتًا)",
    type=["pdf"], accept_multiple_files=True
)

if st.button("فرز"):
    if not uploaded_files:
        st.warning("الرجاء رفع ملف واحد على الأقل")
    else:
        for file in uploaded_files:
            text = ""
            try:
                reader = PdfReader(file)
                for p in reader.pages:
                    t = p.extract_text() or ""
                    text += " " + t
            except Exception as e:
                st.error(f"تعذّر قراءة {file.name}: {e}")
                continue

            low = text.lower()
            ok = all([
                (uni.lower() in low) if uni else True,
                (major.lower() in low) if major else True,
                (nation.lower() in low) if nation else True
            ])

            if ok:
                st.success(f"✅ {file.name} مطابق")
            else:
                st.error(f"❌ {file.name} غير مطابق")