import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import io

# =========================================================
# 1. CONFIGURACIÓN
# =========================================================
st.set_page_config(page_title="MDPA 2026 · HTA Argentina", layout="wide", page_icon="❤️")

AUTOR_APP = "Ricardo Daniel Olano, Especialista en Cardiologia y en Hipertension arterial"

# URL editable desde Streamlit Cloud > Settings > Secrets.
# Importante: usar URL normal de edición de Google Sheets, NO la URL publicada /pubhtml.
URL_PLANILLA_DEFAULT = "https://docs.google.com/spreadsheets/d/1pQVDwWeKH1PKU9eR5mzLJb16cNwqEVENNIr9MyyzWnA/edit?gid=0#gid=0"

def obtener_url_planilla():
    try:
        return st.secrets.get("connections", {}).get("gsheets", {}).get("spreadsheet", URL_PLANILLA_DEFAULT)
    except Exception:
        return URL_PLANILLA_DEFAULT

URL_PLANILLA = obtener_url_planilla()
WORKSHEETS_POSIBLES = ["Pacientes", "Hoja 1", "Hoja1", "Sheet1"]

# ── CSS TEMÁTICA SALUD ────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;600;700;800&family=Playfair+Display:wght@700&display=swap');

:root {
    --blanco:      #FFFFFF;
    --gris-fondo:  #F0F4F8;
    --gris-borde:  #CBD5E1;
    --azul-oscuro: #0B4F8A;
    --azul-medio:  #1976C8;
    --azul-claro:  #D6EAF8;
    --celeste:     #EBF5FF;
    --verde:       #1B7E4A;
    --verde-bg:    #D4EDDA;
    --amarillo:    #856404;
    --amarillo-bg: #FFF3CD;
    --naranja:     #7D3C00;
    --naranja-bg:  #FFE0C2;
    --rojo:        #7B1217;
    --rojo-bg:     #F8D7DA;
    --texto:       #1A2535;
    --texto-suave: #4A5568;
}

html, body, [class*="css"] {
    font-family: 'Nunito', sans-serif !important;
    background-color: var(--gris-fondo) !important;
    color: var(--texto) !important;
}

.stApp { background-color: var(--gris-fondo) !important; }

/* ─── SIDEBAR ──────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0B4F8A 0%, #0d3d6b 60%, #082d52 100%) !important;
    border-right: none !important;
}
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div,
section[data-testid="stSidebar"] label {
    color: #DBEAFE !important;
}
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #FFFFFF !important; }

/* ─── HEADER PRINCIPAL ─────────────────────────────────── */
.app-header {
    background: linear-gradient(135deg, #0B4F8A 0%, #1565C0 60%, #1976C8 100%);
    border-radius: 18px;
    padding: 32px 40px;
    margin-bottom: 28px;
    box-shadow: 0 6px 24px rgba(11,79,138,0.22);
    position: relative;
    overflow: hidden;
}
.app-header::before {
    content: "❤";
    position: absolute;
    right: 40px; top: 50%;
    transform: translateY(-50%);
    font-size: 7em;
    opacity: 0.08;
}
.app-header h1 {
    font-family: 'Playfair Display', serif !important;
    color: #FFFFFF !important; font-size: 2em !important;
    margin: 0 !important; letter-spacing: -0.3px;
}
.app-header p { color: #B3D4F5 !important; margin: 6px 0 0 0 !important; font-size: 0.95em; }

/* ─── TARJETAS DE MEDICIÓN ─────────────────────────────── */
.card {
    background: #FFFFFF;
    border-radius: 14px;
    padding: 22px 24px;
    margin-bottom: 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    border-top: 4px solid;
}
.card-consultorio { border-color: #1976C8; }
.card-mdpa        { border-color: #17A589; }
.card-mapa        { border-color: #7B68EE; }
.card-diurno      { border-color: #F39C12; }
.card-nocturno    { border-color: #5D6D7E; }

.card-title {
    font-weight: 800; font-size: 0.92em;
    letter-spacing: 0.04em; text-transform: uppercase; margin-bottom: 12px;
}
.ct-cons { color: #1976C8; }
.ct-mdpa { color: #17A589; }
.ct-mapa { color: #7B68EE; }
.ct-diu  { color: #F39C12; }
.ct-noc  { color: #5D6D7E; }

/* ─── SEMÁFOROS ────────────────────────────────────────── */
.sema-pill {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-weight: 800;
    font-size: 1.05em;
    margin: 2px 4px;
    letter-spacing: 0.02em;
    border: 2px solid transparent;
}
.sema-verde    { background: var(--verde-bg);    color: var(--verde);    border-color: #1B7E4A; }
.sema-amarillo { background: var(--amarillo-bg); color: var(--amarillo); border-color: #856404; }
.sema-naranja  { background: var(--naranja-bg);  color: var(--naranja);  border-color: #7D3C00; }
.sema-rojo     { background: var(--rojo-bg);     color: var(--rojo);     border-color: #7B1217; }

.sema-label {
    font-size: 0.72em; font-weight: 700;
    letter-spacing: 0.06em; text-transform: uppercase;
    margin-right: 4px; opacity: 0.75;
}

section[data-testid="stSidebar"] .sidebar-sema,
section[data-testid="stSidebar"] .sidebar-sema span,
section[data-testid="stSidebar"] .sidebar-sema b {
    color: #000000 !important;
}
.sema-pill, .sema-pill small, .sema-chip-negro {
    color: #000000 !important;
}

/* ─── PANEL DIAGNÓSTICO ────────────────────────────────── */
.diag-panel {
    background: #FFFFFF;
    border-radius: 14px; padding: 28px 32px; margin-top: 22px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.08);
    border-left: 6px solid #1976C8;
}
.diag-panel h3 { color: #0B4F8A !important; margin-top:0 !important; }

.badge {
    display: inline-block; padding: 8px 22px; border-radius: 24px;
    font-weight: 800; font-size: 1em; letter-spacing: 0.03em;
}
.badge-normal    { background:#D4EDDA; color:#1B7E4A; border:2px solid #1B7E4A; }
.badge-bata      { background:#D6EAF8; color:#1565C0; border:2px solid #1565C0; }
.badge-enmasc    { background:#FFE0C2; color:#7D3C00; border:2px solid #E67E22; }
.badge-sostenida { background:#F8D7DA; color:#7B1217; border:2px solid #C0392B; }

.chip { display:inline-block; padding:3px 12px; border-radius:12px; font-weight:700; font-size:0.82em; }
.chip-b  { background:#D4EDDA; color:#1B7E4A; }
.chip-m  { background:#FFF3CD; color:#856404; }
.chip-ma { background:#FFE0C2; color:#7D3C00; }
.chip-a  { background:#F8D7DA; color:#7B1217; }

/* ─── SECCIÓN TÍTULO ───────────────────────────────────── */
.seccion-titulo {
    background: linear-gradient(90deg, #0B4F8A, #1976C8);
    color: #fff !important; padding: 10px 20px; border-radius: 8px;
    font-weight: 800; font-size: 0.95em; letter-spacing: 0.05em;
    text-transform: uppercase; margin: 22px 0 14px 0;
}

/* ─── INPUTS ───────────────────────────────────────────── */
.stNumberInput input, .stTextInput input {
    background: #FFFFFF !important;
    border: 1.5px solid #B0C4D8 !important;
    color: #1A2535 !important;
    border-radius: 8px !important; font-weight: 600 !important;
}
.stNumberInput input:focus, .stTextInput input:focus {
    border-color: #1976C8 !important;
    box-shadow: 0 0 0 3px rgba(25,118,200,0.15) !important;
}

/* ─── BOTONES ──────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #0B4F8A, #1976C8) !important;
    color: #FFFFFF !important; border: none !important;
    border-radius: 10px !important; padding: 12px 28px !important;
    font-weight: 700 !important; font-size: 0.95em !important;
    box-shadow: 0 4px 14px rgba(11,79,138,0.3) !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(11,79,138,0.4) !important;
}

/* ─── TABS ─────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: #FFFFFF !important; border-radius: 10px !important;
    padding: 4px !important; box-shadow: 0 1px 6px rgba(0,0,0,0.07);
}
.stTabs [data-baseweb="tab"] { color: #4A5568 !important; border-radius: 8px !important; font-weight: 600 !important; }
.stTabs [aria-selected="true"] { background: #0B4F8A !important; color: #FFFFFF !important; }

hr { border-color: #CBD5E1 !important; }
/* Contraste reforzado */
.card, .diag-panel, .stAlert, [data-testid="stMetric"] { color:#111827 !important; }
.card *, .diag-panel *, [data-testid="stMetric"] * { color:#111827 !important; }
.app-header *, .seccion-titulo, .seccion-titulo * { color:#FFFFFF !important; }
.stMarkdown, .stTextInput label, .stNumberInput label, .stCheckbox label { color:#111827 !important; }
input, textarea, select { background:#FFFFFF !important; color:#111827 !important; }
.stTabs [data-baseweb="tab"] p { color:#111827 !important; }
.stTabs [aria-selected="true"] p { color:#FFFFFF !important; }
.autor-app { margin-top:10px; font-size:0.82em; font-weight:700; color:#FFFFFF !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. BASE DE DATOS
# =========================================================
DB_PATH = "usuarios.db"

def normalizar_usuario(usuario):
    return (usuario or "").strip().lower()

def crear_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            usuario TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            matricula TEXT DEFAULT ''
        )
    """)

    c.execute("PRAGMA table_info(usuarios)")
    columnas = [fila[1] for fila in c.fetchall()]
    if "matricula" not in columnas:
        c.execute("ALTER TABLE usuarios ADD COLUMN matricula TEXT DEFAULT ''")

    pw_admin = hashlib.sha256("12345".encode("utf-8")).hexdigest()
    c.execute("""
        INSERT OR IGNORE INTO usuarios (usuario, password, matricula)
        VALUES (?, ?, ?)
    """, ("admin", pw_admin, ""))

    conn.commit()
    conn.close()

def verificar_u(usuario, password):
    usuario = normalizar_usuario(usuario)
    password = (password or "").strip()

    if not usuario or not password:
        return None

    pw = hashlib.sha256(password.encode("utf-8")).hexdigest()

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT usuario, matricula
        FROM usuarios
        WHERE LOWER(TRIM(usuario)) = ?
        AND password = ?
    """, (usuario, pw))

    r = c.fetchone()
    conn.close()

    return dict(r) if r else None

def registrar_usuario(usuario, password, matricula=""):
    usuario = normalizar_usuario(usuario)
    password = (password or "").strip()
    matricula = (matricula or "").strip()

    if not usuario or not password:
        return False, "Debe completar usuario y contraseña."

    pw = hashlib.sha256(password.encode("utf-8")).hexdigest()

    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        c = conn.cursor()

        c.execute("""
            INSERT INTO usuarios (usuario, password, matricula)
            VALUES (?, ?, ?)
        """, (usuario, pw, matricula))

        conn.commit()
        conn.close()

        return True, "Cuenta creada correctamente."

    except sqlite3.IntegrityError:
        return False, "El usuario ya existe. Ingrese con su contraseña."
# =========================================================
# 2. BASE DE DATOS
# =========================================================
crear_db()

if "auth" not in st.session_state:
    st.session_state["auth"] = False
if "user" not in st.session_state:
    st.session_state["user"] = None
if "matricula" not in st.session_state:
    st.session_state["matricula"] = ""

# =========================================================
# 3. GUÍA ARGENTINA HTA 2025 — UMBRALES
# =========================================================
GUIA = {
    "cons":  {"pas": [(140,"verde"),(160,"naranja"),(180,"rojo"),(999,"rojo")],
               "pad": [(90,"verde"),(100,"naranja"),(110,"rojo"),(999,"rojo")],
               "ref_pas":"<140", "ref_pad":"<90", "nombre":"Consultorio"},
    "mdpa":  {"pas": [(135,"verde"),(150,"naranja"),(170,"rojo"),(999,"rojo")],
               "pad": [(85,"verde"),(95,"naranja"),(105,"rojo"),(999,"rojo")],
               "ref_pas":"<135", "ref_pad":"<85", "nombre":"MDPA Domiciliaria"},
    "24h":   {"pas": [(130,"verde"),(145,"naranja"),(165,"rojo"),(999,"rojo")],
               "pad": [(80,"verde"),(90,"naranja"),(100,"rojo"),(999,"rojo")],
               "ref_pas":"<130", "ref_pad":"<80", "nombre":"MAPA 24 horas"},
    "diurno":{"pas": [(135,"verde"),(150,"naranja"),(170,"rojo"),(999,"rojo")],
               "pad": [(85,"verde"),(95,"naranja"),(105,"rojo"),(999,"rojo")],
               "ref_pas":"<135", "ref_pad":"<85", "nombre":"MAPA Diurno"},
    "noct":  {"pas": [(120,"verde"),(135,"naranja"),(155,"rojo"),(999,"rojo")],
               "pad": [(70,"verde"),(80,"naranja"),(90,"rojo"),(999,"rojo")],
               "ref_pas":"<120", "ref_pad":"<70", "nombre":"MAPA Nocturno"},
}

COLORES_SEMA = {
    "verde":    {"bg":"#D4EDDA","txt":"#000000","brd":"#1B7E4A","label":"Normal",   "rgb":(27,126,74)},
    "amarillo": {"bg":"#FFF3CD","txt":"#000000","brd":"#856404","label":"Elevado",  "rgb":(133,100,4)},
    "naranja":  {"bg":"#FFE0C2","txt":"#000000","brd":"#E67E22","label":"Alto",     "rgb":(125,60,0)},
    "rojo":     {"bg":"#F8D7DA","txt":"#000000","brd":"#C0392B","label":"Muy Alto","rgb":(123,18,23)},
}

def nivel(val, umbrales):
    for lim, color in umbrales:
        if val < lim: return color
    return "rojo"

def pill(val, tipo, campo):
    n = nivel(val, GUIA[tipo][campo])
    c = COLORES_SEMA[n]
    return (f'<span class="sema-pill" style="background:{c["bg"]};color:#000000 !important;'
            f'border-color:{c["brd"]};">{val} <small style="font-size:0.7em;font-weight:600;color:#000000 !important;">mmHg</small></span>'
            f'<span class="chip sema-chip-negro" style="background:{c["bg"]};color:#000000 !important;font-size:0.7em;margin-left:2px;">'
            f'{c["label"]}</span>')


# =========================================================
# 4. DIAGNÓSTICO CLÍNICO
# =========================================================
def diagnostico(datos):
    cp,  cd  = datos['c_pas'],    datos['c_pad']
    mp,  md  = datos['m_pas'],    datos['m_pad']
    m24p,m24d= datos['m24_pas'],  datos['m24_pad']
    diap,diad= datos['mdia_pas'], datos['mdia_pad']
    nocp,nocd= datos['mnoc_pas'], datos['mnoc_pad']

    cons_h = cp >= 140 or cd >= 90
    amb_h  = mp >= 135 or md >= 85 or m24p >= 130 or m24d >= 80

    if cons_h and amb_h:
        diag,badge,col_pdf,riesgo = "Hipertensión Arterial Sostenida","badge-sostenida",(155,20,30),"ALTO"
        desc = ("PA elevada en consultorio Y en medición ambulatoria. Requiere evaluación de daño de órgano blanco "
                "e inicio/ajuste de tratamiento farmacológico según Guía Argentina HTA 2025 (SAHA/FAC/SAC).")
    elif cons_h and not amb_h:
        diag,badge,col_pdf,riesgo = "Hipertensión de Guardapolvo Blanco","badge-bata",(21,101,192),"BAJO-MODERADO"
        desc = ("PA elevada solo en consultorio, normal fuera del mismo. La Guía Argentina HTA 2025 recomienda "
                "seguimiento con MDPA/MAPA, modificaciones del estilo de vida y evaluación periódica dado el riesgo "
                "de progresión a HTA sostenida en 5-10 años.")
    elif not cons_h and amb_h:
        diag,badge,col_pdf,riesgo = "Hipertensión Enmascarada","badge-enmasc",(180,70,0),"MODERADO-ALTO"
        desc = ("PA normal en consultorio pero elevada en medición ambulatoria. Entidad de alto riesgo CV según "
                "Guía Argentina HTA 2025: pronóstico similar a HTA sostenida. Requiere tratamiento y seguimiento intensivo.")
    else:
        diag,badge,col_pdf,riesgo = "Normotensión","badge-normal",(27,126,74),"BAJO"
        desc = ("PA dentro de rangos normales en todos los métodos. Mantener controles anuales, estilo de vida "
                "saludable y factores de riesgo controlados según Guía Argentina HTA 2025.")

    descenso = ((diap - nocp) / diap * 100) if diap > 0 else 0
    if   10 <= descenso <= 20: patron,pat_r,col_pat = "Dipper (Normal)",            "Bajo",        (27,126,74)
    elif descenso > 20:         patron,pat_r,col_pat = "Extreme Dipper",             "Moderado",    (133,100,4)
    elif 0 < descenso < 10:    patron,pat_r,col_pat = "Non-Dipper",                 "Moderado-Alto",(180,70,0)
    else:                       patron,pat_r,col_pat = "Riser (Inversión nocturna)", "Muy Alto",    (155,20,30)

    pat_desc = {
        "Dipper (Normal)":            "Descenso fisiológico normal 10-20%. Riesgo CV bajo. Seguimiento habitual.",
        "Extreme Dipper":             "Descenso excesivo >20%. Riesgo de hipoperfusión cerebral y orgánica nocturna. Reevaluar medicación y dosis nocturna.",
        "Non-Dipper":                 "Descenso insuficiente 1-9%. Mayor daño de órgano blanco. Guía Argentina HTA 2025 recomienda cronoterapia.",
        "Riser (Inversión nocturna)": "PA nocturna mayor que diurna. Riesgo CV muy elevado. Tratamiento urgente y referencia especializada.",
    }

    pp_cons = cp - cd; pp_mdpa = mp - md; pp_24h = m24p - m24d

    # ── FACTORES DE RIESGO CV (Guía Argentina HTA 2025) ──────
    frc = datos.get("factores_riesgo", {})
    diabetes          = frc.get("diabetes", False)
    tabaquismo        = frc.get("tabaquismo", False)
    dislipemia        = frc.get("dislipemia", False)
    obesidad          = frc.get("obesidad", False)
    ant_fam_cv        = frc.get("ant_fam_cv", False)
    edad_riesgo       = frc.get("edad_riesgo", False)   # H>55, M>65

    # ── DAÑO ÓRGANO BLANCO (DOB) ────────────────────────────
    dob = datos.get("dano_organo", {})
    hvi               = dob.get("hvi", False)           # Hipertrofia ventricular izquierda
    microalbuminuria  = dob.get("microalbuminuria", False)
    ret_hipertensiva  = dob.get("ret_hipertensiva", False)
    enf_renal_cr      = dob.get("enf_renal_cr", False)  # ERC estadio 3 (TFGe 30-59)

    # ── ENFERMEDAD CV/RENAL ESTABLECIDA ────────────────────
    ece = datos.get("enf_establecida", {})
    erc_avanzada      = ece.get("erc_avanzada", False)  # ERC estadio ≥4 (TFGe <30)
    diabetes_con_dob  = ece.get("diabetes_con_dob", False)
    ecv_establecida   = ece.get("ecv_establecida", False) # IAM, ACV, IC, DAP

    # ── RECALCULAR RIESGO CV con factores clínicos ──────────
    n_frc = sum([diabetes, tabaquismo, dislipemia, obesidad, ant_fam_cv, edad_riesgo])
    tiene_dob = any([hvi, microalbuminuria, ret_hipertensiva, enf_renal_cr])
    tiene_ece = any([erc_avanzada, diabetes_con_dob, ecv_establecida])

    # Meta de PA según perfil (Guía Argentina HTA 2025)
    if diabetes or erc_avanzada or ecv_establecida or diabetes_con_dob:
        meta_pa = "<130/80 mmHg"
    elif enf_renal_cr or microalbuminuria:
        meta_pa = "<130/80 mmHg"
    else:
        meta_pa = "<140/90 mmHg (o <130/80 si tolera)"

    # Reclasificar riesgo CV integrando factores clínicos
    if tiene_ece:
        riesgo = "MUY ALTO"
    elif tiene_dob or (diabetes and not diabetes_con_dob) or (enf_renal_cr):
        riesgo = "ALTO"
    elif cons_h and amb_h and n_frc >= 1:
        riesgo = "ALTO"
    elif n_frc >= 3:
        riesgo = "ALTO"
    elif n_frc in [1,2] and not (cons_h and amb_h):
        riesgo = "MODERADO" if riesgo in ["BAJO","BAJO-MODERADO"] else riesgo
    # else mantiene el riesgo calculado antes por PA

    recs = []
    if amb_h:
        if diabetes or erc_avanzada or ecv_establecida:
            recs.append("Meta de PA <130/80 mmHg dado el alto riesgo CV. Preferir IECA/ARA-II como primer fármaco (Guía Argentina HTA 2025).")
        else:
            recs.append("Iniciar/intensificar tratamiento antihipertensivo: IECA o ARA-II + calcioantagonista o diurético tiazídico (primera línea, Guía Argentina HTA 2025).")
    if patron in ["Non-Dipper","Riser (Inversión nocturna)"]:
        recs.append("Cronoterapia: administrar al menos un fármaco al acostarse (evidencia nivel A, Guía Argentina HTA 2025).")
    if pp_24h > 60:
        recs.append("PP >60 mmHg: evaluar rigidez arterial — solicitar velocidad de onda de pulso (VOP) e índice tobillo-brazo (ITB).")
    if diag == "Hipertensión Enmascarada":
        recs.append("Informar al paciente el alto riesgo CV. Control cada 3 meses con MAPA/MDPA hasta normalización.")
    if diag == "Hipertensión de Guardapolvo Blanco":
        recs.append("Verificar técnica de medición en consultorio. Descartar ansiedad. Repetir MAPA en 12 meses.")
    if datos.get("tratamiento"):
        recs.append("Evaluar adherencia (test de Morisky-Green). Descartar efecto de dosis. Ajustar esquema si PA ambulatoria persiste elevada.")
    # Recomendaciones específicas por factor de riesgo
    if diabetes:
        recs.append("Diabetes: meta PA <130/80 mmHg. IECA/ARA-II de elección (nefroprotección). Control glucémico estricto (HbA1c <7%).")
    if tabaquismo:
        recs.append("Tabaquismo activo: cese tabáquico urgente (mayor beneficio CV que cualquier fármaco). Derivar a programa de cesación.")
    if hvi:
        recs.append("HVI presente: DOB confirmado. Preferir IECA/ARA-II + calcioantagonista. Control ecocardiográfico anual para evaluar regresión.")
    if enf_renal_cr:
        recs.append("ERC estadio 3: meta PA <130/80 mmHg. IECA/ARA-II obligatorio. Monitorear TFGe y kalemia. Evitar AINEs.")
    if erc_avanzada:
        recs.append("ERC avanzada (estadio ≥4): riesgo MUY ALTO. Referencia a nefrología. Meta PA estricta. Ajuste de dosis de fármacos.")
    if ecv_establecida:
        recs.append("Enfermedad CV establecida: meta PA <130/80 mmHg. Estatina + antiagregante según indicación. Control cardiológico.")
    if microalbuminuria:
        recs.append("Microalbuminuria: DOB renal. IECA/ARA-II obligatorio para reducir progresión. Control periódico de albuminuria.")
    if ret_hipertensiva:
        recs.append("Retinopatía hipertensiva: DOB ocular presente. Control oftalmológico semestral. Tratamiento intensivo de PA.")
    if obesidad:
        recs.append("Obesidad: reducción de peso (cada 10 kg = -5-20 mmHg PAS). Dieta DASH + actividad física estructurada.")
    if dislipemia:
        recs.append("Dislipemia: estatina de alta intensidad si riesgo ALTO/MUY ALTO. Meta LDL según categoría de riesgo CV.")
    if not recs:
        recs.append("Controles tensionales anuales. Dieta DASH, actividad física ≥150 min/semana, restricción de sodio <5 g/día.")
    recs.append(f"Meta terapéutica individualizada: {meta_pa} — Estratificar riesgo CV global: glucemia, lípidos, TFGe, microalbuminuria, ECG y fondo de ojo (SAHA 2025).")

    fenotipo_mapa = clasificar_fenotipo_mapa(m24p, m24d, diap, diad, nocp, nocd)
    fenotipo_mapa_texto = texto_fenotipo_mapa(fenotipo_mapa, datos)

    return {
        "diag":diag,"badge":badge,"col_pdf":col_pdf,"riesgo":riesgo,"desc_diag":desc,
        "fenotipo_mapa": fenotipo_mapa, "fenotipo_mapa_texto": fenotipo_mapa_texto,
        "patron":patron,"pat_r":pat_r,"col_pat":col_pat,"pat_desc":pat_desc[patron],"descenso":descenso,
        "pp_cons":pp_cons,"pp_mdpa":pp_mdpa,"pp_24h":pp_24h,"recomendaciones":recs,
        "meta_pa":meta_pa,"n_frc":n_frc,"tiene_dob":tiene_dob,"tiene_ece":tiene_ece,
        "factores_riesgo":frc,"dano_organo":dob,"enf_establecida":ece,
    }



def clasificar_fenotipo_mapa(m24_pas, m24_pad, mdia_pas, mdia_pad, mnoc_pas, mnoc_pad):
    """
    Clasificación EXCLUSIVA del fenotipo hipertensivo por MAPA.
    Umbrales por defecto:
    - 24 h:     >=130/80 mmHg
    - Diurno:   >=135/85 mmHg
    - Nocturno: >=120/70 mmHg

    Devuelve uno solo de los fenotipos permitidos. Si el patrón no encaja
    exactamente en la lista cerrada, devuelve None y se informan solo promedios.
    """
    h24_s = m24_pas >= 130
    h24_d = m24_pad >= 80
    dia_s = mdia_pas >= 135
    dia_d = mdia_pad >= 85
    noc_s = mnoc_pas >= 120
    noc_d = mnoc_pad >= 70

    dia_h = dia_s or dia_d
    noc_h = noc_s or noc_d

    # 1) Fenotipos sostenidos o globales por componente, cuando el patrón compromete día y noche.
    if dia_s and dia_d and noc_s and noc_d and h24_s and h24_d:
        return "HTA SISTODIASTÓLICA SOSTENIDA"

    if dia_s and noc_s and not dia_d and not noc_d and h24_s and not h24_d:
        return "HTA SISTÓLICA AISLADA"

    if dia_d and noc_d and not dia_s and not noc_s and h24_d and not h24_s:
        return "HTA DIASTÓLICA AISLADA"

    # 2) Fenotipos diurnos aislados: el período nocturno debe ser normal.
    if dia_s and dia_d and not noc_h:
        return "HTA SISTODIASTÓLICA DIURNA AISLADA"

    if dia_s and not dia_d and not noc_h:
        return "HTA SISTÓLICA AISLADA DIURNA"

    if dia_d and not dia_s and not noc_h:
        return "HTA DIASTÓLICA AISLADA DIURNA"

    # 3) Fenotipos nocturnos aislados: el período diurno debe ser normal.
    if noc_s and noc_d and not dia_h:
        return "HTA SISTODIASTÓLICA NOCTURNA AISLADA"

    if noc_s and not noc_d and not dia_h:
        return "HTA SISTÓLICA AISLADA NOCTURNA"

    if noc_d and not noc_s and not dia_h:
        return "HTA DIASTÓLICA AISLADA NOCTURNA"

    # 4) Si no corresponde a ninguno de los fenotipos permitidos, no se fuerza diagnóstico.
    return None


def texto_fenotipo_mapa(fenotipo, datos):
    """Texto seguro y no ambiguo para pantalla/PDF."""
    promedios = (
        f"Promedios MAPA: 24 h {datos['m24_pas']}/{datos['m24_pad']} mmHg; "
        f"diurno {datos['mdia_pas']}/{datos['mdia_pad']} mmHg; "
        f"nocturno {datos['mnoc_pas']}/{datos['mnoc_pad']} mmHg."
    )
    if fenotipo:
        return f"Fenotipo MAPA: {fenotipo}. {promedios}"
    return promedios


# =========================================================
# 5. PDF COMPLETO
# =========================================================
VERDE_PDF  = (212,237,218); AMARI_PDF = (255,243,205)
NARAN_PDF  = (255,224,194); ROJO_PDF  = (248,215,218)
AZUL_OSC   = (11,79,138);  AZUL_MED  = (25,118,200)
AZUL_CLR   = (214,234,248);GRIS_CLR  = (240,244,248)
BLANCO     = (255,255,255)

def col_pas(val, tipo):
    for lim, color in GUIA[tipo]["pas"]:
        if val < lim:
            return {"verde":VERDE_PDF,"amarillo":AMARI_PDF,"naranja":NARAN_PDF,"rojo":ROJO_PDF}[color]
    return ROJO_PDF

def col_pad(val, tipo):
    for lim, color in GUIA[tipo]["pad"]:
        if val < lim:
            return {"verde":VERDE_PDF,"amarillo":AMARI_PDF,"naranja":NARAN_PDF,"rojo":ROJO_PDF}[color]
    return ROJO_PDF

def lum(c): return 0.299*c[0]+0.587*c[1]+0.114*c[2]
def tc(c): return (0,0,0) if lum(c) >= 120 else (255,255,255)
def nivel_label(n): return {"verde":"Normal","amarillo":"Elevado","naranja":"Alto","rojo":"Muy Alto"}[n]


def pdf_safe(text):
    if text is None:
        return ""
    text = str(text)
    reemplazos = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2212": "-",
        "\u2265": ">=",
        "\u2264": "<=",
        "\u00a0": " ",
        "\u2022": "-",
        "\u2026": "...",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2192": "->",
        "\u2713": "OK",
    }
    for orig, repl in reemplazos.items():
        text = text.replace(orig, repl)
    return text.encode("latin-1", errors="replace").decode("latin-1")


class HTA_PDF(FPDF):
    def __init__(self, pac, med, fecha):
        super().__init__()
        self.pac = pdf_safe(pac)
        self.med = pdf_safe(med)
        self.fecha = pdf_safe(fecha)

    def cell(self, w, h=0, txt="", border=0, ln=0, align="", fill=False, link=""):
        return super().cell(w, h, pdf_safe(txt), border, ln, align, fill, link)

    def multi_cell(self, w, h, txt="", border=0, align="J", fill=False):
        return super().multi_cell(w, h, pdf_safe(txt), border, align, fill)

    def header(self):
        self.set_fill_color(*AZUL_OSC); self.rect(0,0,210,32,"F")
        self.set_fill_color(*AZUL_MED); self.rect(0,0,4,32,"F")
        self.set_text_color(255,255,255)
        self.set_font("Arial","B",15); self.set_xy(10,5)
        self.cell(0,8,"MDPA 2026 Pro  |  Evaluacion Hemodinamica Integral",ln=True)
        self.set_font("Arial","",9); self.set_xy(10,15)
        self.cell(100,6,f"Paciente: {self.pac}   Dr. {self.med}",ln=False)
        self.cell(0,6,f"Fecha: {self.fecha}   Guia Argentina HTA 2025 (SAHA/FAC/SAC)",ln=True,align="R")
        self.set_draw_color(*AZUL_MED); self.set_line_width(0.8); self.line(0,32,210,32)
        self.set_text_color(0,0,0); self.ln(6)

    def footer(self):
        self.set_y(-14); self.set_fill_color(*AZUL_OSC); self.rect(0,self.get_y()-1,210,16,"F")
        self.set_text_color(180,210,255); self.set_font("Arial","I",7.5)
        self.cell(0,10,
            f"MDPA 2026 Pro  *  Pag. {self.page_no()}  *  {datetime.now().strftime('%d/%m/%Y %H:%M')}  *  "
            "Guia Argentina HTA 2025 (SAHA/FAC/SAC)  *  Uso exclusivo profesional medico",align="C")

    def sec(self, titulo, r=11, g=79, b=138):
        self.ln(3); self.set_fill_color(r,g,b); self.set_text_color(255,255,255)
        self.set_font("Arial","B",10); self.cell(0,9,f"   {titulo}",ln=True,fill=True)
        self.set_text_color(0,0,0); self.ln(3)

    def fila_header(self, cols, widths):
        self.set_fill_color(*AZUL_OSC); self.set_text_color(255,255,255); self.set_font("Arial","B",8.5)
        for col,w in zip(cols,widths):
            self.cell(w,9,col,border=1,align="C",fill=True)
        self.ln(); self.set_text_color(0,0,0)

    def sema_cell(self, w, h, val, color_rgb, ln_after=False):
        self.set_fill_color(*color_rgb); self.set_text_color(*tc(color_rgb))
        self.set_font("Arial","B",9)
        self.cell(w,h,f"{val} mmHg",border=1,align="C",fill=True,ln=1 if ln_after else 0)
        self.set_text_color(0,0,0); self.set_font("Arial","",9)

    def nivel_cell(self, w, h, val, tipo, campo, ln_after=False):
        n   = nivel(val, GUIA[tipo][campo])
        col = {"verde":VERDE_PDF,"amarillo":AMARI_PDF,"naranja":NARAN_PDF,"rojo":ROJO_PDF}[n]
        self.set_fill_color(*col); self.set_text_color(*tc(col)); self.set_font("Arial","B",8)
        self.cell(w,h,nivel_label(n),border=1,align="C",fill=True,ln=1 if ln_after else 0)
        self.set_text_color(0,0,0); self.set_font("Arial","",9)

    def leyenda(self):
        self.ln(2); self.set_font("Arial","B",7.5); self.cell(20,5,"Semaforo:",ln=False)
        for col,label in [(VERDE_PDF,"Normal"),(AMARI_PDF,"Elevado"),(NARAN_PDF,"Alto"),(ROJO_PDF,"Muy Alto")]:
            self.set_fill_color(*col); self.set_text_color(*tc(col)); self.set_font("Arial","B",7.5)
            self.cell(22,5,label,border=0,align="C",fill=True,ln=False)
            self.set_text_color(0,0,0); self.cell(3,5,"",ln=False)
        self.ln(7)


def generar_pdf(datos, res):
    d=datos; r=res
    pdf = HTA_PDF(d['nombre'], d['medico'], d['fecha'])
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page(); pdf.set_font("Arial","",10)

    # ══ 1. DATOS DEL ESTUDIO ══════════════════════════════
    pdf.sec("1. DATOS DEL ESTUDIO Y PACIENTE")
    rows_info = [
        ("Paciente",            d['nombre']),
        ("Medico responsable",  f"Dr. {d['medico']}"),
        ("Matricula medico",    d.get("matricula", "")),
        ("Autor de la app",     AUTOR_APP),
        ("Fecha del estudio",   d['fecha']),
        ("Hora de generacion",  datetime.now().strftime("%H:%M hs")),
        ("Tratamiento activo",  "SI - bajo tratamiento antihipertensivo" if d.get('tratamiento') else "NO - sin tratamiento farmacologico"),
        ("Marco normativo",     "Guia Argentina de HTA 2025 - SAHA / FAC / SAC"),
    ]
    for label, val in rows_info:
        pdf.set_fill_color(*GRIS_CLR); pdf.set_font("Arial","B",9)
        pdf.cell(58,7,label+":",border=0,ln=False,fill=True)
        pdf.set_fill_color(255,255,255); pdf.set_font("Arial","",9)
        pdf.cell(0,7,val,border=0,ln=True)
    pdf.ln(3)

    # ══ 2. TABLA SEMAFORIZADA ════════════════════════════
    pdf.sec("2. VALORES TENSIONALES SEMAFORIZACIÓN - GUIA ARGENTINA HTA 2025")
    cols   = ["Metodo","PAS(mmHg)","Niv.PAS","PAD(mmHg)","Niv.PAD","PP(mmHg)","Niv.PP","Ref.PAS","Ref.PAD"]
    widths = [44,        22,         22,        22,         22,        17,        18,      17,       17]
    pdf.fila_header(cols, widths)

    filas_t = [
        ("Consultorio",          d['c_pas'],    d['c_pad'],    "cons"),
        ("MDPA (Domiciliaria)",  d['m_pas'],    d['m_pad'],    "mdpa"),
        ("MAPA 24 horas",        d['m24_pas'],  d['m24_pad'],  "24h"),
        ("MAPA Diurno",          d['mdia_pas'], d['mdia_pad'], "diurno"),
        ("MAPA Nocturno",        d['mnoc_pas'], d['mnoc_pad'], "noct"),
    ]
    alt = False
    for label,pas,pad,tipo in filas_t:
        pp   = pas - pad
        bg   = GRIS_CLR if not alt else BLANCO
        pp_c = VERDE_PDF if pp<50 else (AMARI_PDF if pp<60 else ROJO_PDF)
        pdf.set_fill_color(*bg); pdf.set_font("Arial","",9)
        pdf.cell(44,8,label,border=1,fill=True)
        pdf.sema_cell(22,8,pas,col_pas(pas,tipo))
        pdf.nivel_cell(22,8,pas,tipo,"pas")
        pdf.sema_cell(22,8,pad,col_pad(pad,tipo))
        pdf.nivel_cell(22,8,pad,tipo,"pad")
        pdf.sema_cell(17,8,pp,pp_c)
        pp_lbl = "Normal" if pp<50 else ("Elevada" if pp<60 else "Alta")
        pdf.set_fill_color(*pp_c); pdf.set_text_color(*tc(pp_c)); pdf.set_font("Arial","B",8)
        pdf.cell(18,8,pp_lbl,border=1,align="C",fill=True)
        pdf.set_text_color(0,0,0); pdf.set_font("Arial","",8)
        pdf.set_fill_color(*AZUL_CLR)
        pdf.cell(17,8,GUIA[tipo]["ref_pas"],border=1,align="C",fill=True)
        pdf.cell(17,8,GUIA[tipo]["ref_pad"],border=1,align="C",fill=True,ln=True)
        alt = not alt
    pdf.leyenda()

    # ══ 3. DIAGNÓSTICO ════════════════════════════════════
    dc = r['col_pdf']
    pdf.sec("3. DIAGNÓSTICO DIFERENCIAL HIPERTENSIVO")
    pdf.set_fill_color(*dc); pdf.set_text_color(*tc(dc)); pdf.set_font("Arial","B",13)
    pdf.cell(0,13,f"  {r['diag'].upper()}   [Riesgo CV: {r['riesgo']}]",border=0,ln=True,fill=True)
    pdf.set_text_color(0,0,0); pdf.ln(4)
    pdf.set_font("Arial","",9); pdf.set_fill_color(*GRIS_CLR)
    pdf.multi_cell(0,6,r['desc_diag'],border=0,fill=True)
    pdf.ln(4)

    # Tabla 2x2
    pdf.set_font("Arial","B",9); pdf.cell(0,6,"Clasificacion segun Guia Argentina HTA 2025:",ln=True); pdf.ln(2)
    pdf.set_fill_color(*AZUL_OSC); pdf.set_text_color(255,255,255); pdf.set_font("Arial","B",8)
    pdf.cell(50,8,"",border=1,fill=True)
    pdf.cell(70,8,"PA Consultorio NORMAL (<140/90)",border=1,align="C",fill=True)
    pdf.cell(70,8,"PA Consultorio ELEVADA (>=140/90)",border=1,align="C",fill=True,ln=True)
    pdf.set_text_color(0,0,0)
    mapa_act = {
        "Normotensión":                     (1,1),
        "Hipertensión de Guardapolvo Blanco":(1,2),
        "Hipertensión Enmascarada":          (2,1),
        "Hipertensión Arterial Sostenida":   (2,2),
    }
    activo = mapa_act.get(r['diag'],(0,0))
    col_celdas = {(1,1):VERDE_PDF,(1,2):AZUL_MED,(2,1):NARAN_PDF,(2,2):ROJO_PDF}
    filas_diag = [
        ("PA Ambulatoria NORMAL", "NORMOTENSION",             "HTA DE GUARDAPOLVO BLANCO"),
        ("PA Ambulatoria ELEVADA","HIPERTENSION ENMASCARADA", "HTA SOSTENIDA"),
    ]
    for ri,(row_label,c1,c2) in enumerate(filas_diag,1):
        pdf.set_fill_color(*AZUL_CLR); pdf.set_text_color(*AZUL_OSC); pdf.set_font("Arial","B",8)
        pdf.cell(50,10,row_label,border=1,fill=True)
        for ci,cell_txt in enumerate([c1,c2],1):
            is_act = (ri==activo[0] and ci==activo[1])
            col_c  = col_celdas.get((ri,ci),GRIS_CLR)
            pfx    = ">>> " if is_act else ""
            sfx    = " <<<" if is_act else ""
            pdf.set_fill_color(*col_c); pdf.set_text_color(*tc(col_c))
            pdf.set_font("Arial","B" if is_act else "",8)
            pdf.cell(70,10,f"{pfx}{cell_txt}{sfx}",border=1,align="C",fill=True)
        pdf.ln()
    pdf.set_text_color(0,0,0); pdf.ln(5)

    # ══ 3B. FENOTIPO HIPERTENSIVO POR MAPA ═════════════
    pdf.sec("3B. CLASIFICACION DEL FENOTIPO HIPERTENSIVO - VALIDO SOLO PARA MAPA")
    pdf.set_font("Arial","",9)
    pdf.multi_cell(0,6,
        "Umbrales MAPA usados por defecto: 24 h >=130/80 mmHg; diurno >=135/85 mmHg; nocturno >=120/70 mmHg.")
    pdf.ln(2)
    if r.get("fenotipo_mapa"):
        pdf.set_fill_color(*ROJO_PDF); pdf.set_text_color(*tc(ROJO_PDF)); pdf.set_font("Arial","B",11)
        pdf.multi_cell(0,9, f"FENOTIPO MAPA: {r.get('fenotipo_mapa')}", border=1, align="C", fill=True)
        pdf.set_text_color(0,0,0); pdf.ln(2)
    else:
        pdf.set_fill_color(*GRIS_CLR); pdf.set_text_color(0,0,0); pdf.set_font("Arial","B",9)
        pdf.multi_cell(0,8, "No corresponde a ninguno de los fenotipos MAPA predefinidos. Se informan solo los promedios.", border=1, fill=True)
        pdf.ln(2)
    pdf.fila_header(["Periodo MAPA", "Promedio PAS", "Promedio PAD", "Umbral MAPA"], [50, 40, 40, 70])
    filas_mapa_fen = [
        ("24 horas", d['m24_pas'], d['m24_pad'], ">=130/80 mmHg"),
        ("Diurno", d['mdia_pas'], d['mdia_pad'], ">=135/85 mmHg"),
        ("Nocturno", d['mnoc_pas'], d['mnoc_pad'], ">=120/70 mmHg"),
    ]
    for per, pas, pad, umb in filas_mapa_fen:
        pdf.set_fill_color(*GRIS_CLR); pdf.set_text_color(0,0,0); pdf.set_font("Arial","",9)
        pdf.cell(50,8,per,border=1,fill=True)
        pdf.cell(40,8,f"{pas} mmHg",border=1,align="C")
        pdf.cell(40,8,f"{pad} mmHg",border=1,align="C")
        pdf.cell(70,8,umb,border=1,align="C",ln=True)
    pdf.ln(5)

    # ══ 4. PATRÓN CIRCADIANO ════════════════════════════
    pc = r['col_pat']
    pdf.sec("4. PATRON CIRCADIANO (DIPPING NOCTURNO)")
    pdf.set_fill_color(*pc); pdf.set_text_color(*tc(pc)); pdf.set_font("Arial","B",11)
    pdf.cell(0,11,f"  {r['patron']}  |  Descenso nocturno: {r['descenso']:.1f}%  |  Riesgo CV: {r['pat_r']}",ln=True,fill=True)
    pdf.set_text_color(0,0,0); pdf.ln(3)
    pdf.set_font("Arial","",9); pdf.set_fill_color(*GRIS_CLR)
    pdf.multi_cell(0,6,r['pat_desc'],fill=True); pdf.ln(4)

    pdf.set_font("Arial","B",9); pdf.cell(0,6,"Clasificacion del patron circadiano:",ln=True); pdf.ln(2)
    pdf.fila_header(["Patron","Descenso","Riesgo CV","Implicacion clinica"],[42,28,28,102])
    pat_tabla = [
        ("Extreme Dipper",   "> 20%", "Moderado",     "Hipoperfusion cerebral. Reevaluar cronoterapia.",       AMARI_PDF),
        ("Dipper (Normal)",  "10-20%","Bajo",          "Patron fisiologico. Seguimiento habitual.",             VERDE_PDF),
        ("Non-Dipper",       "1-9%",  "Mod-Alto",      "Mayor DOB. Guia ARG HTA 2025: agregar dosis nocturna.",NARAN_PDF),
        ("Riser (Inversor)", "< 0%",  "Muy Alto",      "Maximo riesgo CV. Referencia urgente a especialista.",  ROJO_PDF),
    ]
    for p_lbl,desc_d,ries,imp,col_p in pat_tabla:
        is_cur = p_lbl.split()[0] in r['patron']
        bg_f   = col_p if is_cur else GRIS_CLR
        tc_f   = tc(col_p) if is_cur else (0,0,0)
        pdf.set_fill_color(*bg_f); pdf.set_text_color(*tc_f)
        pdf.set_font("Arial","B" if is_cur else "",8.5)
        pdf.cell(42,9,p_lbl,border=1,fill=True)
        pdf.cell(28,9,desc_d,border=1,align="C",fill=True)
        pdf.cell(28,9,ries,border=1,align="C",fill=True)
        pdf.cell(102,9,imp,border=1,fill=True,ln=True)
    pdf.set_text_color(0,0,0); pdf.ln(5)

    # ══ 5. PRESIÓN DE PULSO ═════════════════════════════
    pdf.sec("5. PRESIÓN DE PULSO - MARCADOR DE RIGIDEZ ARTERIAL")
    pdf.set_font("Arial","",9)
    pdf.multi_cell(0,6,
        "PP (PAS-PAD) >60 mmHg es marcador independiente de riesgo CV y sugiere rigidez arterial aumentada. "
        "La Guia Argentina HTA 2025 recomienda evaluar velocidad de onda de pulso (VOP) e indice tobillo-brazo (ITB) ante PP elevada.",
        fill=False); pdf.ln(3)
    pdf.fila_header(["Metodo","PAS","PAD","PP (PAS-PAD)","Interpretacion","Referencia"],[40,22,22,32,52,32])
    pp_tabla = [
        ("Consultorio",         d['c_pas'],   d['c_pad'],   r['pp_cons'],"cons"),
        ("MDPA (Domiciliaria)", d['m_pas'],   d['m_pad'],   r['pp_mdpa'],"mdpa"),
        ("MAPA 24 horas",       d['m24_pas'], d['m24_pad'], r['pp_24h'], "24h"),
    ]
    for m_lbl,pas,pad,pp,tipo in pp_tabla:
        pp_c = VERDE_PDF if pp<50 else (AMARI_PDF if pp<60 else ROJO_PDF)
        pp_i = "Normal (<50)" if pp<50 else ("Lev. elevada (50-59)" if pp<60 else "ELEVADA (>=60) Rigidez")
        pdf.set_font("Arial","",9); pdf.set_fill_color(*GRIS_CLR)
        pdf.cell(40,9,m_lbl,border=1,fill=True)
        pdf.sema_cell(22,9,pas,col_pas(pas,tipo))
        pdf.sema_cell(22,9,pad,col_pad(pad,tipo))
        pdf.sema_cell(32,9,pp,pp_c)
        pdf.set_fill_color(*pp_c); pdf.set_text_color(*tc(pp_c)); pdf.set_font("Arial","B",7.5)
        pdf.cell(52,9,pp_i,border=1,align="C",fill=True)
        pdf.set_fill_color(*AZUL_CLR); pdf.set_text_color(*AZUL_OSC); pdf.set_font("Arial","",8)
        pdf.cell(32,9,"<50 mmHg Normal",border=1,align="C",fill=True,ln=True)
        pdf.set_text_color(0,0,0)
    pdf.ln(5)

    # ══ 6. GRÁFICO COMPARATIVO PAS ══════════════════════
    pdf.sec("6. REPRESENTACION GRAFICA COMPARATIVA DE PAS")
    pdf.set_font("Arial","B",8.5)
    pdf.cell(0,6,"Valores de PAS por metodo vs referencias Guia Argentina HTA 2025:",ln=True); pdf.ln(2)
    met_labels = ["Consultorio","MDPA","MAPA 24h","Diurno","Nocturno"]
    met_tipos  = ["cons","mdpa","24h","diurno","noct"]
    met_pas    = [d['c_pas'],d['m_pas'],d['m24_pas'],d['mdia_pas'],d['mnoc_pas']]
    max_v      = max(met_pas+[170])
    bar_max    = 115
    for ml,mt,mv in zip(met_labels,met_tipos,met_pas):
        bw  = max(2, int((mv/max_v)*bar_max))
        col_b = col_pas(mv, mt)
        pdf.set_font("Arial","",8); pdf.set_text_color(30,30,30)
        pdf.cell(36,8,ml+":",border=0,align="R",ln=False)
        pdf.set_fill_color(*col_b); pdf.cell(bw,8,"",border=0,fill=True,ln=False)
        pdf.set_text_color(*tc(col_b)); pdf.set_font("Arial","B",8)
        pdf.set_xy(pdf.get_x()-bw, pdf.get_y())
        pdf.cell(bw,8,f" {mv}" if bw>14 else "",border=0,fill=False,ln=False)
        pdf.set_text_color(0,0,0); pdf.set_font("Arial","",7.5)
        pdf.cell(22,8,f" {mv} mmHg",border=0,ln=True)
    pdf.set_font("Arial","I",7.5); pdf.set_text_color(80,80,80)
    pdf.cell(0,5,"Ref: Consultorio <140 | MDPA <135 | MAPA 24h <130 | Diurno <135 | Nocturno <120 mmHg (Guia Argentina HTA 2025)",ln=True)
    pdf.set_text_color(0,0,0); pdf.ln(4)

    # ══ 7. RECOMENDACIONES ═════════════════════════════
    pdf.sec("7. RECOMENDACIONES CLINICAS - GUIA ARGENTINA HTA 2025")
    pdf.set_font("Arial","",9)
    for i,rec in enumerate(r['recomendaciones'],1):
        pdf.set_font("Arial","B",9); pdf.cell(10,8,f"{i}.",border=0,ln=False)
        pdf.set_font("Arial","",9); pdf.multi_cell(0,8,rec,border=0)
    pdf.ln(4)

    # ══ 8. ESTRATIFICACIÓN RIESGO ═════════════════════
    pdf.sec("8. ESTRATIFICACIÓN RIESGO CARDIOVASCULAR GLOBAL (SAHA 2025)")
    pdf.set_font("Arial","",9)
    pdf.multi_cell(0,6,
        "La Guia Argentina HTA 2025 recomienda integrar cifras tensionales con factores de riesgo (edad, sexo, "
        "tabaquismo, diabetes, dislipemia, obesidad abdominal, antecedentes familiares), marcadores de dano de "
        "organo blanco (DOB) y enfermedad cardiovascular/renal establecida. El tratamiento se individualiza "
        "segun la categoria de riesgo resultante.")
    pdf.ln(3)

    # ── Tabla: factores del paciente ───────────────────
    frc_p = r.get('factores_riesgo', {})
    dob_p = r.get('dano_organo', {})
    ece_p = r.get('enf_establecida', {})
    frc_items = [
        ("Diabetes mellitus",           frc_p.get("diabetes", False),         "FRC"),
        ("Tabaquismo activo",            frc_p.get("tabaquismo", False),        "FRC"),
        ("Dislipemia",                   frc_p.get("dislipemia", False),        "FRC"),
        ("Obesidad / CC elevada",        frc_p.get("obesidad", False),          "FRC"),
        ("Antecedentes familiares CV",   frc_p.get("ant_fam_cv", False),        "FRC"),
        ("Edad de riesgo (H>55/M>65)",   frc_p.get("edad_riesgo", False),       "FRC"),
        ("HVI (Hipertrofia Ventricular Izq.)", dob_p.get("hvi", False),         "DOB"),
        ("Microalbuminuria 30-300 mg/g", dob_p.get("microalbuminuria", False),  "DOB"),
        ("Retinopatia hipertensiva",     dob_p.get("ret_hipertensiva", False),  "DOB"),
        ("ERC estadio 3 (TFGe 30-59)",   dob_p.get("enf_renal_cr", False),      "DOB"),
        ("ERC estadio >=4 (TFGe <30)",   ece_p.get("erc_avanzada", False),      "ECE"),
        ("Diabetes con DOB",             ece_p.get("diabetes_con_dob", False),  "ECE"),
        ("ECV establecida (IAM/ACV/IC/DAP)", ece_p.get("ecv_establecida", False), "ECE"),
    ]
    cat_colors = {"FRC": AMARI_PDF, "DOB": NARAN_PDF, "ECE": ROJO_PDF}
    cat_labels = {"FRC":"Factor de Riesgo","DOB":"Daño Organo Blanco","ECE":"Enf. CV/Renal Establecida"}
    pdf.fila_header(["Condicion / Factor","Categoria","Presente"], [110, 50, 40])
    for label, presente, cat in frc_items:
        col_cat = cat_colors[cat]
        pdf.set_fill_color(*GRIS_CLR); pdf.set_text_color(0,0,0); pdf.set_font("Arial","",8.5)
        pdf.cell(110, 8, label, border=1, fill=True)
        pdf.set_fill_color(*col_cat); pdf.set_text_color(*tc(col_cat)); pdf.set_font("Arial","B",8)
        pdf.cell(50, 8, cat_labels[cat], border=1, align="C", fill=True)
        si_col = ROJO_PDF if presente else VERDE_PDF
        pdf.set_fill_color(*si_col); pdf.set_text_color(*tc(si_col)); pdf.set_font("Arial","B",9)
        pdf.cell(40, 8, "SI" if presente else "No", border=1, align="C", fill=True, ln=True)
        pdf.set_text_color(0,0,0)
    pdf.ln(3)

    # Meta terapéutica
    meta = r.get('meta_pa', '<140/90 mmHg')
    meta_col = ROJO_PDF if "130" in meta else VERDE_PDF
    pdf.set_font("Arial","B",10)
    pdf.cell(80, 9, "Meta terapeutica individualizada:", border=0, ln=False)
    pdf.set_fill_color(*meta_col); pdf.set_text_color(*tc(meta_col))
    pdf.cell(0, 9, f"  {meta}  ", border=1, align="C", fill=True, ln=True)
    pdf.set_text_color(0,0,0); pdf.ln(4)

    pdf.fila_header(["Categoria","Criterio","Conducta (Guia Argentina HTA 2025)"],[28,78,94])
    pal_r  = {"BAJO":VERDE_PDF,"MODERADO":AMARI_PDF,"ALTO":NARAN_PDF,"MUY ALTO":ROJO_PDF}
    risk_t = [
        ("BAJO",     "Sin factores de riesgo adicionales. PA normal-alta.",           "Cambios estilo de vida. Control anual."),
        ("MODERADO", "1-2 factores de riesgo. Sin DOB ni ECV establecida.",           "Estilo de vida + considerar farmacoterapia."),
        ("ALTO",     ">=3 factores de riesgo, DOB, diabetes o ERC estadio 3.",        "Tratamiento farmacologico. Control c/3 meses."),
        ("MUY ALTO", "ECV establecida, ERC >=4 o diabetes con DOB.",                  "Multifarmaco. Control mensual. Meta PA <130/80."),
    ]
    for cat,crit,cond in risk_t:
        is_act = any(w in r['riesgo'] for w in cat.split())
        col_r  = pal_r[cat]
        bg_f   = col_r if is_act else GRIS_CLR
        tc_f   = tc(col_r) if is_act else (0,0,0)
        pdf.set_fill_color(*bg_f); pdf.set_text_color(*tc_f)
        pdf.set_font("Arial","B" if is_act else "",8.5)
        pdf.cell(28,10,cat,border=1,fill=True,align="C")
        pdf.set_font("Arial","B" if is_act else "",7.5)
        pdf.cell(78,10,crit,border=1,fill=True)
        pdf.cell(94,10,cond,border=1,fill=True,ln=True)
    pdf.set_text_color(0,0,0); pdf.ln(5)

    # ══ 9. FIRMA ════════════════════════════════════
    pdf.sec("9. FIRMA Y RESPONSABILIDAD PROFESIONAL")
    pdf.set_font("Arial","",9)
    pdf.cell(0,7,f"Medico responsable: Dr. {d['medico']}",ln=True)
    pdf.cell(0,7,f"Matricula: {d.get('matricula', '')}",ln=True)
    pdf.cell(0,7,f"Autor de la app: {AUTOR_APP}",ln=True)
    pdf.cell(0,7,f"Fecha de emision: {datetime.now().strftime('%d/%m/%Y')} - Hora: {datetime.now().strftime('%H:%M')}",ln=True)
    pdf.ln(18)
    pdf.set_draw_color(*AZUL_OSC); pdf.set_line_width(0.5); pdf.line(20,pdf.get_y(),100,pdf.get_y())
    pdf.ln(3); pdf.set_font("Arial","I",9)
    pdf.cell(0,5,f"              Firma y sello - Dr. {d['medico']}",ln=True); pdf.ln(6)
    pdf.set_fill_color(*GRIS_CLR); pdf.set_font("Arial","I",7.5); pdf.set_text_color(90,90,90)
    pdf.multi_cell(0,5,
        "AVISO LEGAL: Este informe fue generado por MDPA 2026 Pro como herramienta de apoyo diagnostico "
        "para profesionales de la salud. No reemplaza el criterio clinico del medico tratante. "
        "Los valores de referencia y recomendaciones corresponden a la Guia Argentina de Hipertension Arterial 2025, "
        "publicada por la Sociedad Argentina de Hipertension Arterial (SAHA), la Federacion Argentina de "
        "Cardiologia (FAC) y la Sociedad Argentina de Cardiologia (SAC).",fill=True)
    pdf.set_text_color(0,0,0)
    pdf_str = pdf.output(dest='S')
    if isinstance(pdf_str, bytes):
        return pdf_str
    return pdf_str.encode('latin-1', errors='replace')




# =========================================================
# 6. EXPORTACIÓN A GOOGLE SHEETS Y RESET DE FORMULARIO
# =========================================================
def si_no(valor):
    """Convierte booleanos de Streamlit a texto claro para Google Sheets."""
    return "SI" if bool(valor) else "NO"


def binario(valor):
    """Convierte booleanos a 1/0 para que Google Sheets guarde dato binario real."""
    return 1 if bool(valor) else 0


def activos_texto(diccionario, etiquetas):
    """Devuelve un resumen legible de los ítems marcados."""
    activos = [etiquetas.get(k, k) for k, v in diccionario.items() if bool(v)]
    return " | ".join(activos) if activos else "NO"


def preparar_registro_gs(datos, res):
    """
    Genera un registro PLANO para Google Sheets.
    No se envían diccionarios anidados; cada checkbox clínico se exporta
    como columna binaria real 1/0, más un resumen textual por grupo.
    """
    frc = datos.get("factores_riesgo", {}) or {}
    dob = datos.get("dano_organo", {}) or {}
    ece = datos.get("enf_establecida", {}) or {}

    frc_labels = {
        "diabetes": "Diabetes mellitus",
        "tabaquismo": "Tabaquismo activo",
        "dislipemia": "Dislipemia",
        "obesidad": "Obesidad",
        "ant_fam_cv": "Antecedentes familiares CV",
        "edad_riesgo": "Edad de riesgo",
    }
    dob_labels = {
        "hvi": "HVI",
        "microalbuminuria": "Microalbuminuria",
        "ret_hipertensiva": "Retinopatía hipertensiva",
        "enf_renal_cr": "ERC estadio 3",
    }
    ece_labels = {
        "erc_avanzada": "ERC estadio 4+",
        "diabetes_con_dob": "Diabetes con DOB",
        "ecv_establecida": "ECV establecida",
    }

    return {
        "timestamp_guardado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "nombre": datos.get("nombre", ""),
        "fecha": datos.get("fecha", ""),
        "medico": datos.get("medico", ""),
        "matricula_medico": datos.get("matricula", ""),
        "autor_app": AUTOR_APP,
        "tratamiento_antihipertensivo": binario(datos.get("tratamiento", False)),
        "tratamiento_antihipertensivo_txt": si_no(datos.get("tratamiento", False)),

        "consultorio_pas": datos.get("c_pas"),
        "consultorio_pad": datos.get("c_pad"),
        "mdpa_pas": datos.get("m_pas"),
        "mdpa_pad": datos.get("m_pad"),
        "mapa_24h_pas": datos.get("m24_pas"),
        "mapa_24h_pad": datos.get("m24_pad"),
        "mapa_diurno_pas": datos.get("mdia_pas"),
        "mapa_diurno_pad": datos.get("mdia_pad"),
        "mapa_nocturno_pas": datos.get("mnoc_pas"),
        "mapa_nocturno_pad": datos.get("mnoc_pad"),

        "diagnostico": res.get("diag", ""),
        "fenotipo_mapa": res.get("fenotipo_mapa") or "",
        "fenotipo_mapa_texto": res.get("fenotipo_mapa_texto", ""),
        "riesgo_cv": res.get("riesgo", ""),
        "patron_circadiano": res.get("patron", ""),
        "descenso_nocturno_pct": round(float(res.get("descenso", 0)), 1),
        "presion_pulso_24h": res.get("pp_24h"),
        "meta_pa": res.get("meta_pa", ""),
        "n_factores_riesgo": int(res.get("n_frc", 0)),
        "tiene_dano_organo_blanco": binario(res.get("tiene_dob", False)),
        "tiene_dano_organo_blanco_txt": si_no(res.get("tiene_dob", False)),
        "tiene_enfermedad_cv_renal_establecida": binario(res.get("tiene_ece", False)),
        "tiene_enfermedad_cv_renal_establecida_txt": si_no(res.get("tiene_ece", False)),

        "resumen_factores_riesgo": activos_texto(frc, frc_labels),
        "resumen_dano_organo_blanco": activos_texto(dob, dob_labels),
        "resumen_enfermedad_cv_renal_establecida": activos_texto(ece, ece_labels),

        "frc_diabetes_mellitus": binario(frc.get("diabetes", False)),
        "frc_tabaquismo_activo": binario(frc.get("tabaquismo", False)),
        "frc_dislipemia": binario(frc.get("dislipemia", False)),
        "frc_obesidad": binario(frc.get("obesidad", False)),
        "frc_antecedentes_familiares_cv": binario(frc.get("ant_fam_cv", False)),
        "frc_edad_riesgo": binario(frc.get("edad_riesgo", False)),

        "dob_hvi": binario(dob.get("hvi", False)),
        "dob_microalbuminuria": binario(dob.get("microalbuminuria", False)),
        "dob_retinopatia_hipertensiva": binario(dob.get("ret_hipertensiva", False)),
        "dob_erc_estadio_3": binario(dob.get("enf_renal_cr", False)),

        "ece_erc_estadio_4_o_mayor": binario(ece.get("erc_avanzada", False)),
        "ece_diabetes_con_dob": binario(ece.get("diabetes_con_dob", False)),
        "ece_ecv_establecida": binario(ece.get("ecv_establecida", False)),
    }


def normalizar_dataframe_gs(df_act, registro_gs):
    """Ordena columnas nuevas y elimina columnas antiguas con diccionarios anidados."""
    columnas_nuevas = list(registro_gs.keys())
    df_nuevo = pd.DataFrame([registro_gs])

    if df_act is None or df_act.empty:
        return df_nuevo[columnas_nuevas]

    df_act = df_act.copy()
    df_act = df_act.drop(columns=["factores_riesgo", "dano_organo", "enf_establecida"], errors="ignore")

    for col in columnas_nuevas:
        if col not in df_act.columns:
            df_act[col] = ""

    df_fin = pd.concat([df_act, df_nuevo], ignore_index=True, sort=False)
    columnas_extra = [c for c in df_fin.columns if c not in columnas_nuevas]
    return df_fin[columnas_nuevas + columnas_extra]

def conectar_google_sheets():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        st.session_state.pop("gsheets_error", None)
        return conn
    except Exception as e:
        st.session_state["gsheets_error"] = str(e)
        return None

def leer_google_sheets(conn_gs):
    if conn_gs is None:
        return pd.DataFrame(), None
    ultimo_error = None
    for ws in WORKSHEETS_POSIBLES:
        try:
            try:
                df = conn_gs.read(spreadsheet=URL_PLANILLA, worksheet=ws, ttl=0)
            except TypeError:
                df = conn_gs.read(spreadsheet=URL_PLANILLA, worksheet=ws)
            return (df if df is not None else pd.DataFrame()), ws
        except Exception as e:
            ultimo_error = e
    st.session_state["gsheets_error"] = str(ultimo_error)
    return pd.DataFrame(), None

def guardar_google_sheets(conn_gs, datos, res):
    """
    Guarda un registro en Google Sheets de forma robusta.
    Correcciones principales:
    - Usa URL_PLANILLA normal de edición, no URL publicada /pubhtml.
    - Mantiene columnas binarias 1/0 para FRC, DOB y ECV/renal establecida.
    - Conserva columnas existentes y agrega columnas nuevas sin perder historial.
    """
    if conn_gs is None:
        return False, "Google Sheets no está configurado. Revisá secrets.toml y compartí la planilla con el service account."

    try:
        df_act, worksheet_usada = leer_google_sheets(conn_gs)
        worksheet_usada = worksheet_usada or WORKSHEETS_POSIBLES[0]

        registro_gs = preparar_registro_gs(datos, res)
        df_fin = normalizar_dataframe_gs(df_act, registro_gs)

        columnas_binarias = [
            c for c in df_fin.columns
            if c.startswith(("frc_", "dob_", "ece_"))
            or c in [
                "tratamiento_antihipertensivo",
                "tiene_dano_organo_blanco",
                "tiene_enfermedad_cv_renal_establecida",
            ]
        ]
        for col in columnas_binarias:
            if not col.endswith("_txt") and not col.startswith("resumen_"):
                df_fin[col] = pd.to_numeric(df_fin[col], errors="coerce").fillna(0).astype(int)

        # Limpieza final para evitar errores de serialización en Google Sheets.
        df_fin = df_fin.fillna("")

        try:
            conn_gs.update(
                spreadsheet=URL_PLANILLA,
                worksheet=worksheet_usada,
                data=df_fin,
            )
        except TypeError:
            # Compatibilidad con versiones anteriores del conector.
            conn_gs.update(
                worksheet=worksheet_usada,
                data=df_fin,
            )

        return True, f"Guardado en Google Sheets, hoja: {worksheet_usada}."

    except Exception as e:
        st.session_state["gsheets_error"] = str(e)
        return False, f"No se pudo guardar en Google Sheets: {e}"


CAMPOS_EVALUACION_DEFAULTS = {
    "nombre_paciente": "",
    "matricula_medico": "",
    "cpas": 120, "cpad": 80,
    "tratamiento": False,
    "mpas": 115, "mpad": 75,
    "m24s": 125, "m24d": 75,
    "mdias": 130, "mdiad": 80,
    "mnocs": 110, "mnocd": 65,
    "frc_diabetes": False,
    "frc_tabaquismo": False,
    "frc_dislipemia": False,
    "frc_obesidad": False,
    "frc_ant_fam": False,
    "frc_edad": False,
    "dob_hvi": False,
    "dob_microalb": False,
    "dob_ret": False,
    "dob_erc3": False,
    "ece_erc_av": False,
    "ece_dm_dob": False,
    "ece_ecv": False,
}


def resetear_evaluacion():
    """Restablece todos los campos del formulario a sus valores iniciales."""
    for clave, valor in CAMPOS_EVALUACION_DEFAULTS.items():
        st.session_state[clave] = valor
    # Mantiene la matrícula del médico logueado para no tener que cargarla nuevamente.
    st.session_state["matricula_medico"] = st.session_state.get("matricula", "") or ""

# =========================================================
# 6. INTERFAZ PRINCIPAL
# =========================================================
def mostrar_interfaz():
    conn_gs = conectar_google_sheets()

    # ── SIDEBAR ───────────────────────────────────────
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center;padding:24px 0 16px;">
            <div style="font-size:3.2em;">❤️</div>
            <div style="font-size:1.15em;font-weight:800;color:#fff;margin-top:6px;">Dr. {st.session_state['user']}</div>
            <div style="font-size:0.78em;color:#93C5FD;letter-spacing:0.05em;text-transform:uppercase;margin-top:2px;">MDPA 2026 Pro</div>
            <div style="font-size:0.76em;color:#F8FAFC;margin-top:4px;">Matrícula: {st.session_state.get('matricula', '') or 'No informada'}</div>
            <div class="autor-app">{AUTOR_APP}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("**🇦🇷 Guía Argentina HTA 2025**")
        st.markdown("""
        <div style="font-size:0.8em;line-height:2.2em;color:#BFDBFE;">
        🏥 <b>Consultorio:</b> &lt;140/90 mmHg<br>
        🏠 <b>MDPA:</b> &lt;135/85 mmHg<br>
        ⌚ <b>MAPA 24h:</b> &lt;130/80 mmHg<br>
        ☀️ <b>MAPA Diurno:</b> &lt;135/85 mmHg<br>
        🌙 <b>MAPA Nocturno:</b> &lt;120/70 mmHg
        </div>""", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("**🚦 Semáforo de valores**")
        st.markdown("""
        <div class="sidebar-sema" style="font-size:0.8em;line-height:2.4em;">
        <span style="background:#D4EDDA;color:#000000 !important;padding:3px 12px;border-radius:10px;font-weight:700;border:1px solid #1B7E4A;">🟢 Normal</span><br>
        <span style="background:#FFF3CD;color:#000000 !important;padding:3px 12px;border-radius:10px;font-weight:700;border:1px solid #856404;">🟡 Elevado</span><br>
        <span style="background:#FFE0C2;color:#000000 !important;padding:3px 12px;border-radius:10px;font-weight:700;border:1px solid #7D3C00;">🟠 Alto</span><br>
        <span style="background:#F8D7DA;color:#000000 !important;padding:3px 12px;border-radius:10px;font-weight:700;border:1px solid #7B1217;">🔴 Muy Alto</span>
        </div>""", unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state["auth"] = False
            st.session_state["user"] = None
            st.session_state["matricula"] = ""
            st.rerun()

    # ── HEADER ────────────────────────────────────────
    st.markdown("""
    <div class="app-header">
        <h1>❤️ MDPA 2026 Pro</h1>
        <p>Sistema de Evaluación Hemodinámica · <strong>Guía Argentina de Hipertensión Arterial 2025</strong> · SAHA / FAC / SAC</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Nueva Evaluación", "📚 Historial"])

    with tab1:
        col_reset_1, col_reset_2 = st.columns([1, 3])
        with col_reset_1:
            if st.button("🧹 Nueva evaluación", use_container_width=True):
                resetear_evaluacion()
                st.rerun()

        nombre = st.text_input("👤 Nombre completo del paciente", placeholder="Ej.: García, Juan Carlos", key="nombre_paciente")
        st.markdown('<div class="seccion-titulo">📊 Ingreso de Valores Tensionales</div>', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="card card-consultorio"><div class="card-title ct-cons">🏥 Consultorio</div>', unsafe_allow_html=True)
            cpas = st.number_input("PAS (mmHg)", 70, 250, 120, key="cpas")
            cpad = st.number_input("PAD (mmHg)", 30, 150, 80,  key="cpad")
            trat = st.toggle("💊 Bajo tratamiento antihipertensivo", key="tratamiento")
            st.markdown(f'<div style="margin-top:10px;"><span class="sema-label">PAS</span>{pill(cpas,"cons","pas")}&nbsp;&nbsp;<span class="sema-label">PAD</span>{pill(cpad,"cons","pad")}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="card card-mdpa"><div class="card-title ct-mdpa">🏠 MDPA Domiciliaria</div>', unsafe_allow_html=True)
            mpas = st.number_input("PAS (mmHg)", 70, 250, 115, key="mpas")
            mpad = st.number_input("PAD (mmHg)", 30, 150, 75,  key="mpad")
            st.markdown(f'<div style="margin-top:10px;"><span class="sema-label">PAS</span>{pill(mpas,"mdpa","pas")}&nbsp;&nbsp;<span class="sema-label">PAD</span>{pill(mpad,"mdpa","pad")}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c3:
            st.markdown('<div class="card card-mapa"><div class="card-title ct-mapa">⌚ MAPA 24 Horas</div>', unsafe_allow_html=True)
            m24s = st.number_input("PAS (mmHg)", 70, 250, 125, key="m24s")
            m24d = st.number_input("PAD (mmHg)", 30, 150, 75,  key="m24d")
            st.markdown(f'<div style="margin-top:10px;"><span class="sema-label">PAS</span>{pill(m24s,"24h","pas")}&nbsp;&nbsp;<span class="sema-label">PAD</span>{pill(m24d,"24h","pad")}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        col_dia, col_noc = st.columns(2)
        with col_dia:
            st.markdown('<div class="card card-diurno"><div class="card-title ct-diu">☀️ MAPA Diurno</div>', unsafe_allow_html=True)
            mdia_s = st.number_input("PAS (mmHg)", 70, 250, 130, key="mdias")
            mdia_d = st.number_input("PAD (mmHg)", 30, 150, 80,  key="mdiad")
            st.markdown(f'<div style="margin-top:10px;"><span class="sema-label">PAS</span>{pill(mdia_s,"diurno","pas")}&nbsp;&nbsp;<span class="sema-label">PAD</span>{pill(mdia_d,"diurno","pad")}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_noc:
            st.markdown('<div class="card card-nocturno"><div class="card-title ct-noc">🌙 MAPA Nocturno</div>', unsafe_allow_html=True)
            mnoc_s = st.number_input("PAS (mmHg)", 70, 250, 110, key="mnocs")
            mnoc_d = st.number_input("PAD (mmHg)", 30, 150, 65,  key="mnocd")
            st.markdown(f'<div style="margin-top:10px;"><span class="sema-label">PAS</span>{pill(mnoc_s,"noct","pas")}&nbsp;&nbsp;<span class="sema-label">PAD</span>{pill(mnoc_d,"noct","pad")}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ── SECCIÓN: FACTORES DE RIESGO CV ──────────────────
        st.markdown('<div class="seccion-titulo">⚠️ Factores de Riesgo Cardiovascular · Guía Argentina HTA 2025</div>', unsafe_allow_html=True)
        st.markdown("<small style='color:#64748B;'>Completar para estratificación de riesgo CV integrada y metas terapéuticas individualizadas (SAHA/FAC/SAC 2025)</small>", unsafe_allow_html=True)

        col_frc1, col_frc2, col_frc3 = st.columns(3)

        with col_frc1:
            st.markdown("**🩺 Factores de Riesgo Clásicos**")
            frc_diabetes    = st.checkbox("🩸 Diabetes mellitus", key="frc_diabetes")
            frc_tabaquismo  = st.checkbox("🚬 Tabaquismo activo", key="frc_tabaquismo")
            frc_dislipemia  = st.checkbox("🧪 Dislipemia", key="frc_dislipemia")
            frc_obesidad    = st.checkbox("⚖️ Obesidad (IMC ≥30 o CC elevada)", key="frc_obesidad")
            frc_ant_fam     = st.checkbox("👨‍👩‍👧 Antecedentes familiares CV prematuros", key="frc_ant_fam")
            frc_edad        = st.checkbox("🎂 Edad de riesgo (H >55a / M >65a)", key="frc_edad")

        with col_frc2:
            st.markdown("**🫀 Daño de Órgano Blanco (DOB)**")
            dob_hvi         = st.checkbox("💓 HVI — Hipertrofia Ventricular Izquierda", key="dob_hvi")
            dob_microalb    = st.checkbox("🫘 Microalbuminuria (30-300 mg/g)", key="dob_microalb")
            dob_ret         = st.checkbox("👁️ Retinopatía hipertensiva", key="dob_ret")
            dob_erc3        = st.checkbox("🫘 ERC estadio 3 (TFGe 30-59 ml/min)", key="dob_erc3")

        with col_frc3:
            st.markdown("**🚨 Enfermedad CV/Renal Establecida**")
            ece_erc_av      = st.checkbox("⛔ ERC estadio 4+ (TFGe <30 ml/min)", key="ece_erc_av")
            ece_dm_dob      = st.checkbox("🩸 Diabetes con daño de órgano blanco", key="ece_dm_dob")
            ece_ecv         = st.checkbox("❤️ ECV establecida (IAM/ACV/IC/DAP)", key="ece_ecv")

        factores_riesgo_dict = {
            "diabetes": frc_diabetes, "tabaquismo": frc_tabaquismo,
            "dislipemia": frc_dislipemia, "obesidad": frc_obesidad,
            "ant_fam_cv": frc_ant_fam, "edad_riesgo": frc_edad,
        }
        dano_organo_dict = {
            "hvi": dob_hvi, "microalbuminuria": dob_microalb,
            "ret_hipertensiva": dob_ret, "enf_renal_cr": dob_erc3,
        }
        enf_establecida_dict = {
            "erc_avanzada": ece_erc_av, "diabetes_con_dob": ece_dm_dob,
            "ecv_establecida": ece_ecv,
        }

        # Diagnóstico en tiempo real
        datos_actuales = {
            "nombre": nombre or "Sin especificar", "fecha": datetime.now().strftime("%d/%m/%Y"),
            "medico": st.session_state['user'],
            "matricula": st.session_state.get("matricula", ""),
            "tratamiento": trat,
            "c_pas": cpas,    "c_pad": cpad,
            "m_pas": mpas,    "m_pad": mpad,
            "m24_pas": m24s,  "m24_pad": m24d,
            "mdia_pas": mdia_s,"mdia_pad": mdia_d,
            "mnoc_pas": mnoc_s,"mnoc_pad": mnoc_d,
            "factores_riesgo": factores_riesgo_dict,
            "dano_organo": dano_organo_dict,
            "enf_establecida": enf_establecida_dict,
        }
        res = diagnostico(datos_actuales)

        st.markdown('<div class="diag-panel">', unsafe_allow_html=True)
        st.markdown("### 🔍 Diagnóstico Diferencial · Tiempo Real · Guía Argentina HTA 2025")
        col_d1,col_d2,col_d3,col_d4 = st.columns([2,1,1,1])
        with col_d1:
            st.markdown(f'<span class="{res["badge"]}">{res["diag"]}</span>', unsafe_allow_html=True)
        with col_d2:
            pal = {"BAJO":"chip-b","MODERADO":"chip-m","ALTO":"chip-ma","MUY ALTO":"chip-a","BAJO-MODERADO":"chip-m","MODERADO-ALTO":"chip-ma"}
            st.markdown(f'Riesgo CV: <span class="chip {pal.get(res["riesgo"],"chip-m")}">{res["riesgo"]}</span>', unsafe_allow_html=True)
        with col_d3:
            st.markdown(f"**Patrón:** `{res['patron']}`  \nDescenso: `{res['descenso']:.1f}%`")
        with col_d4:
            pp_c = "chip-b" if res['pp_24h']<50 else ("chip-m" if res['pp_24h']<60 else "chip-a")
            st.markdown(f'PP 24h: <span class="chip {pp_c}">{res["pp_24h"]} mmHg</span>', unsafe_allow_html=True)

        st.markdown("#### 🧭 Clasificación del fenotipo hipertensivo · válido solo para MAPA")
        st.markdown("<small style='color:#64748B;'>Umbrales: 24 h ≥130/80 mmHg · diurno ≥135/85 mmHg · nocturno ≥120/70 mmHg</small>", unsafe_allow_html=True)
        if res.get("fenotipo_mapa"):
            st.markdown(f'<span class="badge badge-sostenida">{res["fenotipo_mapa"]}</span>', unsafe_allow_html=True)
        else:
            st.info("No corresponde a ninguno de los fenotipos MAPA predefinidos. Se informan solo los promedios.")
        st.markdown(f"**Promedios MAPA:** 24 h `{m24s}/{m24d} mmHg` · diurno `{mdia_s}/{mdia_d} mmHg` · nocturno `{mnoc_s}/{mnoc_d} mmHg`")
        # Chips de factores de riesgo activos
        frc_activos = []
        frc_labels = {"diabetes":"Diabetes","tabaquismo":"Tabaquismo","dislipemia":"Dislipemia",
                      "obesidad":"Obesidad","ant_fam_cv":"Ant.Fam CV","edad_riesgo":"Edad riesgo"}
        dob_labels  = {"hvi":"HVI","microalbuminuria":"Microalbuminuria",
                       "ret_hipertensiva":"Retinopatia","enf_renal_cr":"ERC estadio 3"}
        ece_labels  = {"erc_avanzada":"ERC >=4","diabetes_con_dob":"DM+DOB","ecv_establecida":"ECV estab."}
        for k,v in res['factores_riesgo'].items():
            if v: frc_activos.append(f"<span class='chip chip-m'>{frc_labels.get(k,k)}</span>")
        for k,v in res['dano_organo'].items():
            if v: frc_activos.append(f"<span class='chip chip-ma'>{dob_labels.get(k,k)}</span>")
        for k,v in res['enf_establecida'].items():
            if v: frc_activos.append(f"<span class='chip chip-a'>{ece_labels.get(k,k)}</span>")
        if frc_activos:
            st.markdown(f"<div style='margin:8px 0 4px;'><b>⚠️ Condicionantes activos:</b>&nbsp; {'&nbsp;'.join(frc_activos)}</div>", unsafe_allow_html=True)
        meta_pal = "chip-b" if "140" in res['meta_pa'] else "chip-a"
        st.markdown(f"<div style='margin:4px 0 10px;'><b>🎯 Meta terapéutica:</b> <span class='chip {meta_pal}'>{res['meta_pa']}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#374151;font-size:0.9em;margin-top:8px;'>{res['desc_diag']}</p>", unsafe_allow_html=True)
        st.markdown("**💡 Recomendaciones** *(Guía Argentina HTA 2025 — SAHA/FAC/SAC)*:")
        for rec in res['recomendaciones']:
            st.markdown(f"<span style='color:#1565C0;font-weight:700;'>▶</span> {rec}", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col_b1,_,_ = st.columns([1,1,2])
        with col_b1:
            if st.button("💾 Guardar y Generar PDF", use_container_width=True):
                if not nombre:
                    st.warning("⚠️ Ingresá el nombre del paciente antes de guardar.")
                else:
                    ok_gs, msg_gs = guardar_google_sheets(conn_gs, datos_actuales, res)
                    if ok_gs:
                        st.success("✅ " + msg_gs)
                    else:
                        st.error("⚠️ " + msg_gs)
                        with st.expander("Configuración necesaria para Google Sheets"):
                            st.code("""# .streamlit/secrets.toml
[connections.gsheets]
spreadsheet = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSkpTq2JhFI21b5IMSn8tl96dG2OGe_ec26rXRnXKL6CtMbrOeL08ynALgepcJEf4kGaSanUaj_RBEN/pubhtml"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "...@...iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
""", language="toml")
                    pdf_bytes = generar_pdf(datos_actuales, res)
                    st.download_button(
                        label="📄 Descargar Informe PDF Completo",
                        data=pdf_bytes,
                        file_name=f"HTA_{nombre.replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                        use_container_width=True)
                    st.balloons()

    with tab2:
        st.markdown("### 📚 Historial de Pacientes")
        if conn_gs:
            try:
                df, ws = leer_google_sheets(conn_gs)
                if df.empty:
                    st.info("📭 Sin datos guardados todavía.")
                else:
                    st.caption(f"Hoja conectada: {ws}")
                    st.dataframe(df, use_container_width=True, hide_index=True)
            except:
                st.info("📭 Sin datos o sin conexión a Google Sheets.")
        else:
            st.info("📭 Conexión a Google Sheets no configurada.")


# =========================================================
# 7. LOGIN
# =========================================================
if not st.session_state["auth"]:

    st.markdown(f"""
    <div style="max-width:520px;margin:60px auto 0;background:#fff;border-radius:20px;
                padding:40px 44px;box-shadow:0 8px 32px rgba(11,79,138,0.13);border-top:6px solid #0B4F8A;">
        <div style="text-align:center;margin-bottom:28px;">
            <div style="font-size:3.5em;">❤️</div>
            <h2 style="font-family:'Playfair Display',serif;color:#0B4F8A;margin:10px 0 4px;">MDPA 2026 Pro</h2>
            <p style="color:#111827;font-size:0.88em;margin:0;">
                Guía Argentina de Hipertensión Arterial 2025<br>SAHA / FAC / SAC
            </p>
            <p style="color:#111827;font-size:0.82em;font-weight:700;margin-top:10px;">
                Autor: {AUTOR_APP}
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    _, col_c, _ = st.columns([1, 1.6, 1])

    with col_c:
        t1, t2 = st.tabs(["🔑 Ingresar", "📝 Registrarse"])

        with t1:
            with st.form("form_login", clear_on_submit=False):
                u = st.text_input("Usuario médico", placeholder="usuario", key="login_usuario")
                p = st.text_input("Contraseña", type="password", placeholder="••••••••", key="login_password")
                ingresar = st.form_submit_button("Ingresar al sistema", use_container_width=True)

            if ingresar:
                usuario_ok = verificar_u(u, p)

                if usuario_ok:
                    st.session_state["auth"] = True
                    st.session_state["user"] = usuario_ok.get("usuario", normalizar_usuario(u))
                    st.session_state["matricula"] = usuario_ok.get("matricula", "") or ""
                    st.success("✅ Ingreso correcto.")
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas o campos incompletos.")

        with t2:
            with st.form("form_registro", clear_on_submit=False):
                nu = st.text_input("Apellido y nombre del médico", placeholder="Dr. Apellido", key="reg_usuario")
                nm = st.text_input("Matrícula médica", placeholder="Ej.: MP 123456", key="reg_matricula")
                np = st.text_input("Contraseña nueva", type="password", placeholder="••••••••", key="reg_password")
                crear = st.form_submit_button("Crear cuenta médica", use_container_width=True)

            if crear:
                ok, mensaje = registrar_usuario(nu, np, nm)

                if ok:
                    st.session_state["auth"] = True
                    st.session_state["user"] = normalizar_usuario(nu)
                    st.session_state["matricula"] = (nm or "").strip()
                    st.success("✅ Cuenta creada e ingreso correcto.")
                    st.rerun()
                else:
                    st.warning("⚠️ " + mensaje)

    st.markdown(f"""
    <div style="text-align:center;color:#111827;font-size:0.78em;margin-top:30px;">
        MDPA 2026 Pro · Herramienta de apoyo diagnóstico · Uso exclusivo del profesional médico<br>
        {AUTOR_APP}
    </div>
    """, unsafe_allow_html=True)

else:
    mostrar_interfaz()
