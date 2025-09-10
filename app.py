import streamlit as st
from io import BytesIO
from PyPDF2 import PdfReader
import docx2txt
import pandas as pd
import openpyxl

# تهيئة الصفحة
st.set_page_config(page_title="صفوة لفرز السير الذاتية", page_icon="📝", layout="centered")
st.title("✨ صفوة لفرز السير الذاتية ✨")

# خانات الإدخال
uni = st.text_input("الجامعة")
major = st.text_input("التخصص")
nation = st.text_input("الجنسية")

# رفع الملفات
uploaded_files = st.file_uploader("✨ ارفع ملفات السير الذاتية (PDF, DOCX, XLSX)", 
                                  type=["pdf", "docx", "xlsx"], 
                                  accept_multiple_files=True)

if st.button("فرز"):
    if not uploaded_files:
        st.warning("الرجاء رفع ملف واحد على الأقل")
    else:
        for file in uploaded_files:
            content = ""

            # قراءة PDF
            if file.name.endswith(".pdf"):
                pdf = PdfReader(file)
                for page in pdf.pages:
                    content += page.extract_text()

            # قراءة DOCX
            elif file.name.endswith(".docx"):
                content = docx2txt.process(file)

            # قراءة Excel
            elif file.name.endswith(".xlsx"):
                df = pd.read_excel(file)
                content = " ".join(df.astype(str).fillna("").values.flatten())

            # التحقق من الشروط
            conditions = [
                (uni.lower() in content.lower()) if uni else True,
                (major.lower() in content.lower()) if major else True,
                (nation.lower() in content.lower()) if nation else True
            ]

            if all(conditions):
                st.success(f"✅ {file.name} مطابق للشروط")
            else:
                st.error(f"❌ {file.name} غير مطابق")