# app.py
import streamlit as st
from io import BytesIO
from pathlib import Path

from PyPDF2 import PdfReader
import docx2txt

# ---------- إعداد الصفحة ----------
st.set_page_config(page_title="صفوة لفرز السير الذاتية", layout="centered")

st.title("صفوة لفرز السير الذاتية")

# ---------- دوال مساعدة ----------
AR_DIACS = "".join([
    "\u064B","\u064C","\u064D","\u064E","\u064F","\u0650","\u0651","\u0652",
    "\u0653","\u0654","\u0655","\u0670","\u0640"  # التشكيل + التطويل
])

def normalize_ar(s: str) -> str:
    if not s: return ""
    # حروف بدائل + إزالة التشكيل/التطويل
    s = s.replace("أ","ا").replace("إ","ا").replace("آ","ا")
    s = s.replace("ى","ي").replace("ؤ","و").replace("ئ","ي").replace("ة","ه")
    s = "".join(ch for ch in s if ch not in AR_DIACS)
    return s.lower().strip()

def read_pdf(file) -> str:
    try:
        reader = PdfReader(file)
        pages = []
        for p in reader.pages:
            try:
                pages.append(p.extract_text() or "")
            except Exception:
                pages.append("")
        return "\n".join(pages)
    except Exception:
        # أحياناً نحتاج ننسخ البايتات أول
        try:
            data = file.read()
            file.seek(0)
            reader = PdfReader(BytesIO(data))
            return "\n".join([(p.extract_text() or "") for p in reader.pages])
        except Exception:
            return ""

def read_docx(file) -> str:
    try:
        # docx2txt يحتاج مسار، فنكتب ملف مؤقت داخل الذاكرة
        data = file.read()
        file.seek(0)
        tmp = BytesIO(data)
        # docx2txt لا يقرأ BytesIO مباشرة، لذا نحفظ مؤقتاً لو كان متاح
        # في كلود ستريملت ما عندنا نظام ملفات دائم، فنكتفي بالمحاولة البديلة:
        return docx2txt.process(file) or ""
    except Exception:
        return ""

def read_txt(file) -> str:
    try:
        return file.read().decode("utf-8", errors="ignore")
    except Exception:
        try:
            return file.read().decode("cp1256", errors="ignore")
        except Exception:
            return ""

def read_file_text(up):
    name = (up.name or "").lower()
    if name.endswith(".pdf"):
        return read_pdf(up)
    if name.endswith(".docx"):
        return read_docx(up)
    if name.endswith(".txt"):
        return read_txt(up)
    # أنواع أخرى حالياً نتجاهلها (CSV/XLSX يمكن نفعّلها لاحقاً)
    return ""

def parse_keywords(s: str):
    # يفصل بـ , أو / أو | أو مسافة مسمّنة
    if not s: return []
    parts = [p.strip() for p in s.replace("|",",").replace("/",",").split(",")]
    return [p for p in parts if p]

NATION_SYNONYMS = {
    "saudi": {"سعودي","سعوديه","سعودية","سعوديون","Saudi","KSA","Saudi Arabia","Saudiarabia","saudi"},
    "non":   {"غير سعودي","غير سعوديه","غير-سعودي","Non-Saudi","Non Saudi","non saudi","غيرسعودي"}
}

def match_nation(text_norm: str, want: str) -> bool:
    if not want: 
        return True
    want = normalize_ar(want)
    # إذا كتب المستخدم كلمة مباشرة (سعودي / غير سعودي):
    if "سعود" in want or "ksa" in want or "saudi" in want:
        group = "saudi"
    elif "غير" in want or "non" in want:
        group = "non"
    else:
        # إذا كتب حر قبل، نبحث كما هو
        return want in text_norm
    # طابقة مرادفات
    for cand in NATION_SYNONYMS["saudi" if group=="saudi" else "non"]:
        if normalize_ar(cand) in text_norm:
            return True
    return False

# ---------- نموذج الإدخال ----------
col1, col2 = st.columns(2)
with col1:
    uni = st.text_input("الجامعة", placeholder="مثال: جامعة الملك سعود")
with col2:
    major = st.text_input("التخصص", placeholder="مثال: نظم معلومات إدارية")

nation = st.text_input("الجنسية", placeholder="مثال: سعودي / Non-Saudi")
extra  = st.text_input("كلمات إضافية (اختياري)", placeholder="مثال: خبرة، تدريب صيفي")

st.write("**ارفاق ملفات CV (PDF / DOCX / TXT)**")
uploads = st.file_uploader(
    "اسحبي وأفلتي هنا أو اختاري ملفات",
    type=["pdf","docx","txt"],
    accept_multiple_files=True
)

if st.button("ابدأ الفرز الآن"):
    if not uploads:
        st.warning("حمّلي ملف واحد على الأقل.")
    else:
        uni_n   = normalize_ar(uni)
        major_n = normalize_ar(major)
        extra_keys = [normalize_ar(k) for k in parse_keywords(extra)]
        nation_raw = nation  # نحتاج الخام للدالة

        for up in uploads:
            content = read_file_text(up)
            content_n = normalize_ar(content)

            # شروط المطابقة (شرط موجود => لازم يتحقق)
            conditions = []
            if uni_n:
                conditions.append(uni_n in content_n)
            if major_n:
                conditions.append(major_n in content_n)
            if nation_raw.strip():
                conditions.append(match_nation(content_n, nation_raw))
            for k in extra_keys:
                conditions.append(k in content_n)

            ok = all(conditions) if conditions else False

            if ok:
                st.success(f"✅ مطابق للشروط: {up.name}")
            else:
                st.error(f"❌ غير مطابق: {up.name}")