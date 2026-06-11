import streamlit as st
import easyocr
import difflib
from PIL import Image, ImageOps, ImageEnhance
import numpy as np
import re

# 1. Веб-беттің негізгі баптаулары
st.set_page_config(
    page_title="Камерамен код тексеру", 
    page_icon="📸", 
    layout="wide"
)

st.title("📸 Камера арқылы Python кодтарын тексеру панелі")
st.write("🧑‍🏫 **Нұсқаулық:** Оқушылардың жұмысын камерамен тікелей суретке түсіріңіз немесе дайын файлдарды жүктеңіз. Жүйе оларды өзара салыстырады.")

# 2. OCR Модельді іске қосу (Кэштеу)
@st.cache_resource
def load_ocr_model():
    return easyocr.Reader(['en'])

try:
    reader = load_ocr_model()
except Exception as e:
    st.error(f"OCR Моделін жүктеу қатесі: {e}")

# --- КӨМЕКШІ ФУНКЦИЯЛАР ---

# А. Суретті тазалау және контрастын арттыру
def preprocess_image(pil_image):
    # 1. Суретті ақ-қара (серый деңгейге) айналдыру
    gray_img = ImageOps.grayscale(pil_image)
    # 2. Мәтін мен артқы фон анық бөлінуі үшін контрасты 2.5 есе арттыру
    enhancer = ImageEnhance.Contrast(gray_img)
    enhanced_img = enhancer.enhance(2.5)
    return enhanced_img

# Ә. Кодты плагиатқа тексермес бұрын нормализациялау (тазалау)
def normalize_python_code(code_str):
    # 1. Комментарийлерді өшіру (# таңбасынан басталатын)
    code_str = re.sub(r'#.*', '', code_str)
    # 2. Артық бос жолдар мен шеткі бос орындарды тазалау
    lines = [line.strip() for line in code_str.split('\n') if line.strip()]
    return "\n".join(lines)


# 3. Басқару панелі (Сол жақта)
st.sidebar.header("⚙️ Баптаулар")
similarity_threshold = st.sidebar.slider("🔴 Қауіпті деңгей шегі (%)", min_value=50, max_value=100, value=75)
warning_threshold = st.sidebar.slider("🟡 Ескерту деңгейі шегі (%)", min_value=30, max_value=50, value=45)

if "student_database" not in st.session_state:
    st.session_state.student_database = {}

# 4. СҮРЕТТІ ЖӘНЕ КОДТЫ ҚАБЫЛДАУДЫҢ ҮШ ЖОЛЫ
tabs = st.tabs([
    "📷 Тікелей Камерамен түсіру", 
    "📁 Дайын файлдарды жаппай жүктеу", 
    "💻 Оқушының өз кодын енгізуі"
])

# --- 1-ТАБ: КАМЕРАМЕН ТҮСІРУ ---
with tabs[0]:
    st.subheader("Оқушының жұмысын камераға түсіру")
    student_name_input = st.text_input("Оқушының аты-жөнін жазыңыз (мысалы: Асан, Үсен):", key="name_input")
    camera_file = st.camera_input("Кодты суретке түсіріңіз")
    
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

# --- 2-ТАБ: ФАЙЛДАРДЫ ЖҮКТЕУ ---
with tabs[1]:
    st.subheader("Дайын файлдарды компьютерден жүктеу")
    uploaded_files = st.file_uploader(
        "Файлдарды таңдаңыз (Файл аты оқушының аты болуы керек)", 
        type=["jpg", "png", "jpeg"], 
        accept_multiple_files=True
    )
    
    if uploaded_files:
        if st.button("📁 Файлдарды өңдеу және енгізу"):
            for file in uploaded_files:
                raw_img = Image.open(file)
                processed_img = preprocess_image(raw_img)
                img_np = np.array(processed_img)
                result = reader.readtext(img_np, detail=0)
                detected_code = "\n".join(result)
                cleaned_code = normalize_python_code(detected_code)
                s_name = file.name.split('.')[0]
                st.session_state.student_database[s_name] = cleaned_code
            st.success(f"✅ {len(uploaded_files)} файл нормализацияланып базаға қосылды!")
            st.rerun()

# --- 3-ТАБ: ОҚУШЫНЫҢ ӨЗ КОДЫН ТІКЕЛЕЙ ЕНГІЗУІ (ЖАҢА) ---
with tabs[2]:
    st.subheader("🧑‍🎓 Оқушының өз кодын мәтін түрінде енгізу терезесі")
    st.info("💡 Мұнда оқушы өз кодын тікелей жаза алады немесе IDLE/VS Code-тан көшіріп қоя алады.")
    
    student_name_direct = st.text_input("Аты-жөніңізді енгізіңіз (мысалы: Әлихан):", key="name_direct")
    direct_code = st.text_area("Кодыңызды осы жерге жазыңыз немесе қойыңыз:", height=250, key="code_direct")
    
    if st.button("💻 Жұмысты тексеруге жіберу"):
        if student_name_direct.strip() and direct_code.strip():
            s_name = student_name_direct.strip()
            
            # Оқушының кодын да қауіпсіздік үшін нормализациядан (тазалаудан) өткіземіз
            cleaned_code = normalize_python_code(direct_code)
            
            st.session_state.student_database[s_name] = cleaned_code
            st.success(f"✅ {s_name}, сіздің кодыңыз сәтті қабылданды! Төмендегі жалпы тізімге қосылды.")
            st.rerun()
        else:
            st.warning("⚠️ Өтініш, аты-жөніңізді және код өрісін толық толтырыңыз!")


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
                
                # Нормализацияланған мәтіндерді салыстыру
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
