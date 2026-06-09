import streamlit as st
import easyocr
import difflib
from PIL import Image
import numpy as np

# 1. Веб-беттің негізгі баптаулары
st.set_page_config(
    page_title="Код Плагиат Антивирус", 
    page_icon="🖥️", 
    layout="wide"
)

# Стильдерді әдемілеу (CSS)
st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    </style>
    """, unsafe_allow_html=True)

st.title("🖥️ Python Кодтарының Плагиатын Тексеру Веб-Панелі")
st.write("🧑‍🏫 **Мұғалімдерге арналған құрал:** Оқушылардың жұмыс суреттерін бірден белгілеп жүктеңіз. Жүйе оларды өзара салыстырып, көшіргендерді анықтайды.")

# 2. Суреттен мәтін оқитын (OCR) модельді іске қосу (Жылдам жұмыс істеу үшін кэштеледі)
@st.cache_resource
def load_ocr_model():
    return easyocr.Reader(['en'])

try:
    reader = load_ocr_model()
except Exception as e:
    st.error(f"OCR Моделін жүктеу қатесі: {e}")

# 3. Файлдарды қабылдау бөлімі
st.sidebar.header("⚙️ Басқару панелі")
similarity_threshold = st.sidebar.slider("🔴 Қауіпті деңгей шегі (%)", min_value=50, max_value=100, value=75)
warning_threshold = st.sidebar.slider("🟡 Ескерту деңгейі шегі (%)", min_value=30, max_value=50, value=45)

uploaded_files = st.file_uploader(
    "Оқушылардың код түсірілген суреттерін таңдаңыз (Бірнешеуін бірге белгілеуге болады)", 
    type=["jpg", "png", "jpeg"], 
    accept_multiple_files=True
)

# 4. Басты логика және есептеулер
if uploaded_files:
    if len(uploaded_files) < 2:
        st.info("💡 Салыстыру жүргізу үшін кем дегенде **2 оқушының суретін** жүктеуіңіз керек.")
    else:
        st.success(f"📚 Жүйеге {len(uploaded_files)} оқушының жұмысы қабылданды.")
        
        # Контейнерлер құру
        database = {}
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # СҮРЕТТЕРДЕН КОДТЫ ШЫҒАРУ ЖӘНЕ ТАЗАЛАУ
        for idx, file in enumerate(uploaded_files):
            status_text.text(f"⏳ Сурет өңделуде ({idx+1}/{len(uploaded_files)}): {file.name}")
            
            try:
                # Суретті оқу
                image = Image.open(file)
                image_np = np.array(image)
                
                # OCR арқылы кодты мәтінге айналдыру
                result = reader.readtext(image_np, detail=0)
                raw_code = "\n".join(result)
                
                # Файл атауынан оқушының атын алу (мысалы, 'Асан.jpg' -> 'Асан')
                student_name = file.name.split('.')[0]
                database[student_name] = raw_code
                
            except Exception as e:
                st.error(f"❌ {file.name} файлын оқу мүмкін болмады: {e}")
            
            # Прогресс жолағын жаңарту
            progress_bar.progress((idx + 1) / len(uploaded_files))
            
        status_text.text("✅ Барлық суреттер сәтті өңделді! Плагиат деңгейін есептеу басталды...")
        progress_bar.empty()
        
        # БАРЛЫҚ КОДТАРДЫ ӨЗАРА САЛЫСТЫРУ (ALL-TO-ALL)
        results_list = []
        student_names = list(database.keys())
        
        for i in range(len(student_names)):
            for j in range(i + 1, len(student_names)):
                name1 = student_names[i]
                name2 = student_names[j]
                
                # Екі мәтінді салыстыру алгоритмі
                matcher = difflib.SequenceMatcher(None, database[name1], database[name2])
                similarity = matcher.ratio() * 100
                
                results_list.append({
                    "student1": name1,
                    "student2": name2,
                    "similarity": round(similarity, 2)
                })
                
        # Нәтижелерді ұқсастық пайызы бойынша жоғарыдан төмен қарай сұрыптау
        results_list = sorted(results_list, key=lambda x: x['similarity'], reverse=True)
        
        # 5. НӘТИЖЕНІ ЭКРАНҒА ӘДЕМІ ШЫҒАРУ
        st.subheader("📊 Салыстыру қорытындысы және Көшіру Рейтингі")
        
        for res in results_list:
            # Тексеру пайызына байланысты визуалды безендіру
            if res['similarity'] >= similarity_threshold:
                # 🔴 ҚАУІПТІ ДЕҢГЕЙ
                st.error(f"🚨 **ҚАУІПТІ:** **{res['student1']}** және **{res['student2']}** кодтарында өте жоғары ұқсастық бар! **Ұқсастық: {res['similarity']}%**")
            elif res['similarity'] >= warning_threshold:
                # 🟡 ЕСКЕРТУ ДЕҢГЕЙІ
                st.warning(f"⚠️ **ЕСКЕРТУ:** **{res['student1']}** және **{res['student2']}** кодтарында жартылай сәйкестік бар. **Ұқсастық: {res['similarity']}%**")
            else:
                # 🟢 ҚАЛЫПТЫ ДЕҢГЕЙ
                st.success(f"✅ **ҚАЛЫПТЫ:** **{res['student1']}** мен **{res['student2']}** жұмыстары өзгеше. **Ұқсастық: {res['similarity']}%**")
                
            # Екі оқушының кодын қатар қойып салыстыру терезесі (Спойлер)
            with st.expander(f"🔍 {res['student1']} және {res['student2']} кодтарын ашып қарау"):
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader(f"👤 {res['student1']} коды:")
                    st.code(database[res['student1']], language="python")
                with col2:
                    st.subheader(f"👤 {res['student2']} коды:")
                    st.code(database[res['student2']], language="python")
        
        status_text.text("🎉 Тексеру толық аяқталды!")
