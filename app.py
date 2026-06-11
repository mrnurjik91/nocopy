import streamlit as st
import easyocr
import difflib
from PIL import Image, ImageOps, ImageEnhance
import numpy as np
import re

# 1. Веб-беттің негізгі баптаулары
st.set_page_config(
    page_title="Академиялық адалдық: Код тексеру", 
    page_icon="📸", 
    layout="wide"
)

st.title("📸 Камера және Файлдар арқылы Python кодтарын тексеру панелі")
st.write("🧑‍🏫 **Жобаның мақсаты:** Оқушылар арасындағы академиялық адалдықты сақтау, плагиатты анықтау және кодтарды әділ салыстыру.")

# 2. OCR Модельді іске қосу (Кэштеу - жылдам жұмыс істеу үшін)
@st.cache_resource
def load_ocr_model():
    return easyocr.Reader(['en'])

try:
    reader = load_ocr_model()
except Exception as e:
    st.error(f"OCR Моделін жүктеу қатесі: {e}")

# --- КӨМЕКШІ ФУНКЦИЯЛАР ---

# А. Суретті тазалау және анықтығын арттыру (Камера мен СҮРЕТТЕР үшін)
def preprocess_image(pil_image):
    gray_img = ImageOps.grayscale(pil_image)
    enhancer = ImageEnhance.Contrast(gray_img)
    enhanced_img = enhancer.enhance(2.5)
    return enhanced_img

# Ә. Кодты плагиатқа тексермес бұрын нормализациялау (тазалау)
def normalize_python_code(code_str):
    # 1. Комментарийлерді өшіру (# таңбасынан басталатын жолдар)
    code_str = re.sub(r'#.*', '', code_str)
    # 2. Артық бос жолдар мен шеткі бос орындарды тазалау
    lines = [line.strip() for line in code_str.split('\n') if line.strip()]
    return "\n".join(lines)


# 3. Басқару панелі (Сол жақта)
st.sidebar.header("⚙️ Баптаулар")
similarity_threshold = st.sidebar.slider("🔴 Қауіпті деңгей шегі (%)", min_value=50, max_value=100, value=75)
warning_threshold = st.sidebar.slider("🟡 Ескерту деңгейі шегі (%)", min_value=30, max_value=50, value=45)

# Сессияны іске қосу
if "student_database" not in st.session_state:
    st.session_state.student_database = {}

# 4. ДЕРЕКТЕРДІ ҚАБЫЛДАУДЫҢ 4 ТҮРЛІ ЖОЛЫ (ТАБТАР)
tabs = st.tabs([
    "📷 Тікелей Камерамен түсіру", 
    "📁 Сурет файлдарын жүктеу", 
    "📄 .py / .txt файлдарын жүктеу",
    "💻 Оқушының өз кодын жазуы"
])

# --- 1-ТАБ: ТЕЛЕФОН КАМЕРАСЫ НЕМЕСЕ ГАЛЕРИЯ (ЖАҢАРТЫЛҒАН) ---
with tabs[0]:
    st.subheader("📱 Телефон камерасымен түсіру немесе Галереядан таңдау")
    st.info("💡 Смартфонмен кірсеңіз, төмендегі батырманы басқанда телефонның өз камерасы немесе галереясы ашылады.")
    
    student_name_input = st.text_input("Оқушының аты-жөнін жазыңыз (мысалы: Асан, Үсен):", key="name_input")
    
    # st.camera_input-ті файл жүктеушіге ауыстырдық, бірақ ұялы телефондар үшін баптадық
    camera_file = st.file_uploader(
        "📷 Суретке тікелей түсіріңіз немесе Галереядан жүктеңіз", 
        type=["jpg", "png", "jpeg"],
        key="mobile_camera_uploader"
    )
    
    if camera_file and student_name_input:
        student_name = student_name_input.strip()
        session_key = f"raw_ocr_{student_name}"
        
        if session_key not in st.session_state:
            raw_img = Image.open(camera_file)
            processed_img = preprocess_image(raw_img)
            img_np = np.array(processed_img)
            
            with st.spinner(f"{student_name} коды өңделуде..."):
                result = reader.readtext(img_np, detail=0)
                st.session_state[session_key] = "\n".join(result)
        
        edited_code = st.text_area(
            "📝 Танылған код (Қателерді осы жерден түзетіп жіберсеңіз болады):", 
            value=st.session_state[session_key], 
            height=200
        )
        
        if st.button("📸 Осы жұмысты базаға ресми қосу"):
            cleaned_code = normalize_python_code(edited_code)
            st.session_state.student_database[student_name] = cleaned_code
            st.success(f"✅ {student_name} жұмысы сақталды!")
            del st.session_state[session_key]
            st.rerun()
# --- 2-ТАБ: СУРЕТ ФАЙЛДАРЫН ЖҮКТЕУ ---
with tabs[1]:
    st.subheader("Дайын сурет файлдарын компьютерден жүктеу")
    uploaded_images = st.file_uploader(
        "Суреттерді таңдаңыз (Файл аты оқушының аты болуы керек)", 
        type=["jpg", "png", "jpeg"], 
        accept_multiple_files=True,
        key="image_uploader"
    )
    
    if uploaded_images:
        if st.button("📁 Суреттерді өңдеу және енгізу"):
            for file in uploaded_images:
                raw_img = Image.open(file)
                processed_img = preprocess_image(raw_img)
                img_np = np.array(processed_img)
                result = reader.readtext(img_np, detail=0)
                detected_code = "\n".join(result)
                cleaned_code = normalize_python_code(detected_code)
                s_name = file.name.split('.')[0]
                st.session_state.student_database[s_name] = cleaned_code
            st.success(f"✅ {len(uploaded_images)} сурет файл базаға қосылды!")
            st.rerun()

# --- 3-ТАБ: .PY НЕПЕСЕ .TXT ФАЙЛДАРЫН ЖҮКТЕУ (ЖАҢА) ---
with tabs[2]:
    st.subheader("📄 Python (.py) немесе Мәтіндік (.txt) файлдарды жаппай жүктеу")
    st.info("💡 Файл атауы оқушының аты-жөні болуы керек. Мысалы: Мадияр.py немесе Аружан.txt")
    
    uploaded_code_files = st.file_uploader(
        "Код файлдарын таңдаңыз (.py, .txt)", 
        type=["py", "txt"], 
        accept_multiple_files=True,
        key="code_file_uploader"
    )
    
    if uploaded_code_files:
        if st.button("📄 Файлдарды оқу және базаға енгізу"):
            for file in uploaded_code_files:
                try:
                    # Файлды цифрлық мәтін түрінде оқу (декодтау)
                    file_contents = file.read().decode("utf-8")
                    
                    # Кодты тазалау
                    cleaned_code = normalize_python_code(file_contents)
                    
                    # Файл форматын алып тастап, тек оқушының атын сақтау
                    s_name = file.name.split('.')[0]
                    st.session_state.student_database[s_name] = cleaned_code
                except Exception as e:
                    st.error(f"❌ {file.name} файлын оқу кезінде қате шықты: {e}")
            
            st.success(f"✅ {len(uploaded_code_files)} код файлы базаға сәтті қосылды!")
            st.rerun()

# --- 4-ТАБ: ОҚУШЫНЫҢ ӨЗ КОДЫН ТІКЕЛЕЙ ЕНГІЗУІ ---
with tabs[3]:
    st.subheader("🧑‍🎓 Оқушының өз кодын мәтін түрінде енгізу терезесі")
    student_name_direct = st.text_input("Аты-жөніңізді енгізіңіз:", key="name_direct")
    direct_code = st.text_area("Кодыңызды осы жерге жазыңыз немесе қойыңыз (Copy-Paste):", height=200, key="code_direct")
    
    if st.button("💻 Жұмысты тексеруге жіберу"):
        if student_name_direct.strip() and direct_code.strip():
            s_name = student_name_direct.strip()
            cleaned_code = normalize_python_code(direct_code)
            st.session_state.student_database[s_name] = cleaned_code
            st.success(f"✅ {s_name}, сіздің кодыңыз қабылданды!")
            st.rerun()
        else:
            st.warning("⚠️ Аты-жөніңізді және код өрісін толтырыңыз!")

# --- 5. БАЗАНЫ КӨРУ ЖӘНЕ ТАЗАЛАУ ---
if st.session_state.student_database:
    st.sidebar.write("---")
    st.sidebar.subheader("🗂️ Базадағы оқушылар:")
    for name in st.session_state.student_database.keys():
        st.sidebar.write(f"- {name}")
        
    if st.sidebar.button("🗑️ Базаны толық тазалау"):
        st.session_state.student_database = {}
        st.rerun()

    # --- 6. ПЛАГИАТТЫ ЕСЕПТЕУ (ALL-TO-ALL) ---
    st.markdown("---")
    st.header("📊 Салыстыру қорытындысы")
    
    current_db = st.session_state.student_database
    student_names = list(current_db.keys())
    
    if len(student_names) < 2:
        st.info("💡 Салыстыруды бастау үшін базада кем дегенде **2 оқушының жұмысы** болуы керек.")
    else:
        results_list = []
        for i in range(len(student_names)):
            for j in range(i + 1, len(student_names)):
                name1 = student_names[i]
                name2 = student_names[j]
                
                # Тазаланған кодтарды өзара салыстыру
                matcher = difflib.SequenceMatcher(None, current_db[name1], current_db[name2])
                similarity = matcher.ratio() * 100
                
                results_list.append({
                    "student1": name1,
                    "student2": name2,
                    "similarity": round(similarity, 2)
                })
                
        results_list = sorted(results_list, key=lambda x: x['similarity'], reverse=True)
        
        for res in results_list:
            if res['similarity'] >= similarity_threshold:
                st.error(f"🚨 **ҚАУІПТІ:** **{res['student1']}** және **{res['student2']}** — **Ұқсастық: {res['similarity']}%**")
            elif res['similarity'] >= warning_threshold:
                st.warning(f"⚠️ **ЕСКЕРТУ:** **{res['student1']}** және **{res['student2']}** — **Ұқсастық: {res['similarity']}%**")
            else:
                st.success(f"✅ **ҚАЛЫПТЫ:** **{res['student1']}** мен **{res['student2']}** — **Ұқсастық: {res['similarity']}%**")
                
            with st.expander(f"🔍 {res['student1']} және {res['student2']} кодтарын салыстыру"):
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader(f"👤 {res['student1']} коды:")
                    st.code(current_db[res['student1']], language="python")
                with col2:
                    st.subheader(f"👤 {res['student2']} коды:")
                    st.code(current_db[res['student2']], language="python")
