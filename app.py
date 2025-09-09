# app.py
import streamlit as st
from io import BytesIO
from pathlib import Path

# مكتبات استخراج نصوص
import PyPDF2
import docx2txt

st.set_page_config(page_title="صفحة فلترة السِير", layout="centered")

st.title("صفحة فلترة السِير — نسخة بسيطة")

# Inputs (اللي تبغيه تظهر كـ placeholder)
uni = st.text_input("الجامعة", placeholder="مثال: King Saud University")
nation = st.text_input("الجنسية", placeholder="مثال: سعودي")
major = st.text_input("التخصص", placeholder="مثال: نظم المعلومات الإدارية")
extra = st.text_input("كلمات إضافية (اختياري)", placeholder="مثال: تدريب صيفي")

st.markdown("---")
uploaded = st.file_uploader("إرفاق CV (PDF أو DOCX)", type=["pdf", "docx"])

def extract_text_from_pdf(file_bytes):
    try:
        reader = PyPDF2.PdfReader(BytesIO(file_bytes))
        text = []
        for p in reader.pages:
            text.append(p.extract_text() or "")
        return "\n".join(text)
    except Exception as e:
        return ""

def extract_text_from_docx(file_bytes):
    try:
        # docx2txt يحتاج ملف على قرص، فنكتب مؤقت ثم نقرأه
        tmp = "temp_doc.docx"
        with open(tmp, "wb") as f:
            f.write(file_bytes)
        text = docx2txt.process(tmp)
        Path(tmp).unlink(missing_ok=True)
        return text
    except Exception as e:
        return ""

if uploaded:
    st.info("جاري قراءة الملف...")
    file_bytes = uploaded.read()
    name = uploaded.name.lower()

    if name.endswith(".pdf"):
        content = extract_text_from_pdf(file_bytes).lower()
    elif name.endswith(".docx"):
        content = extract_text_from_docx(file_bytes).lower()
    else:
        content = ""

    # تحقق الشروط البسيطة (لو الحقول فاضية نتجاهلها)
    checks = [
        (uni.strip().lower() in content) if uni.strip() else True,
        (major.strip().lower() in content) if major.strip() else True,
        (nation.strip().lower() in content) if nation.strip() else True,
        (extra.strip().lower() in content) if extra.strip() else True,
    ]

    if all(checks) and content.strip():
        st.success(f"✅ {uploaded.name} مطابق للشروط (مكتوب في الملف).")
        st.download_button("نزّل الملف الأصلي", data=file_bytes, file_name=uploaded.name)
    else:
        st.error(f"❌ {uploaded.name} غير مطابق (لم نعثر على الشروط داخل الملف).")
        st.write("— قم بتجربة ملف آخر أو تأكد من أن الكلمات مكتوبة بنفس الصيغة داخل الـ CV.")

else:
    st.write("اختر ملف CV لتجربته — هذا التطبيق نسخة أبسط لضمان التشغيل.")