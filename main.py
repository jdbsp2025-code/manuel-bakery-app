import streamlit as st
import base64
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import sys

# --- FUNCIONES DE RUTA SEGURA ---

def resource_path(relative_path):
    """ Encuentra los iconos dentro del ejecutable """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def obtener_ruta_datos(nombre_archivo):
    """ Guarda los datos en AppData para que NO se borren al actualizar """
    carpeta_segura = os.path.join(os.environ['APPDATA'], 'COMUNAPP')
    if not os.path.exists(carpeta_segura):
        os.makedirs(carpeta_segura)
    return os.path.join(carpeta_segura, nombre_archivo)

# --- IMPORTACIÓN DE MÓDULOS ---
# Asegúrate de que estos archivos estén en la misma carpeta
import login  
import modulo_ventas
import modulo_inventario
import modulo_ingresos  
import modulo_tasas
import modulo_cierres
import modulo_nomina
import modulo_seguridad 

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Panadería Comunal Lanceros Atures", layout="wide", initial_sidebar_state="collapsed")

# --- FUNCIONES DE APOYO ---
def obtener_tasa_bcv():
    try:
        requests.packages.urllib3.disable_warnings()
        url = "https://www.bcv.org.ve/"
        response = requests.get(url, verify=False, timeout=5) 
        soup = BeautifulSoup(response.content, 'html.parser')
        tasa_elemento = soup.find('div', id='dolar').find('strong')
        tasa_str = tasa_elemento.text.strip().replace(',', '.')
        return round(float(tasa_str), 2)
    except: 
        return 36.50

def get_base64_img(file_path):
    full_path = resource_path(file_path)
    if os.path.exists(full_path):
        with open(full_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

# --- INICIALIZACIÓN DE MEMORIA ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'usuario_actual' not in st.session_state: st.session_state.usuario_actual = ""
if 'menu_principal' not in st.session_state: st.session_state.menu_principal = "Escritorio"
if 'tasa_bcv' not in st.session_state: st.session_state.tasa_bcv = obtener_tasa_bcv()
if 'turno_actual' not in st.session_state: st.session_state.turno_actual = "TURNO NO ASIGNADO"

# --- LOGIN ---
if not st.session_state.autenticado:
    login.mostrar_login()
    st.stop()  

# --- CSS ---
st.markdown("""
    <style>
    .stApp { background-color: white; }
    [data-testid="stHeader"] { display: none !important; }
    .barra-global {
        background-color: #68A042; color: white; padding: 15px; border-radius: 8px;
        display: flex; justify-content: space-between; align-items: center;
        font-family: Arial, sans-serif; font-weight: bold;
    }
    .cabecera-roja {
        display: flex; align-items: center; justify-content: center;
        gap: 25px; border: 3px solid #e0b0b0; border-radius: 20px;
        padding: 15px; margin-bottom: 35px; background-color: #fff9f9;
    }
    .logo-cabecera { height: 80px; width: auto; }
    div[data-testid="column"] button {
        height: 80px !important; border-radius: 12px; font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- BARRA SUPERIOR ---
ahora = datetime.now()
tasa_f = f"{st.session_state.tasa_bcv:,.2f}".replace('.', ',')
col_i, col_s = st.columns([8.5, 1.5]) 
with col_i:
    st.markdown(f'<div class="barra-global"><span>FECHA: {ahora.strftime("%d/%m/%Y %H:%M")} | USUARIO: {st.session_state.usuario_actual.upper()}</span><span style="background-color: #5B9BD5; padding: 5px 20px; border-radius: 5px;">{st.session_state.turno_actual}</span><span style="background-color: #A9D18E; color: black; padding: 5px 20px; border-radius: 5px;">$ : {tasa_f} BS</span></div>', unsafe_allow_html=True)

with col_s:
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

# --- ESCRITORIO ---
if st.session_state.menu_principal == "Escritorio":
    img_l1 = get_base64_img("assets/logo_ures.png")
    img_l2 = get_base64_img("assets/logo_barrio.png")
    img_v = get_base64_img("assets/ventas.png")
    img_i = get_base64_img("assets/inventario.PNG")
    img_ing = get_base64_img("assets/ingresos.png") 
    img_t = get_base64_img("assets/TASAS_BCV.png")
    img_c = get_base64_img("assets/cierre.png") 
    img_n = get_base64_img("assets/nomina.png") 
    img_seg = get_base64_img("assets/seguridad.png")

    st.markdown(f'<div class="cabecera-roja"><img src="data:image/png;base64,{img_l1}" class="logo-cabecera"><h1 style="font-size: 38px; color: #444;">Panadería Comunal Lanceros Atures</h1><img src="data:image/png;base64,{img_l2}" class="logo-cabecera"></div>', unsafe_allow_html=True)

    # Botones de Módulos
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div style='text-align:center;'><img src='data:image/png;base64,{img_v}' width='100'></div>" if img_v else "🛒", unsafe_allow_html=True)
        if st.button("🛒 VENTAS", use_container_width=True): st.session_state.menu_principal = "Ventas"; st.rerun()
    with c2:
        st.markdown(f"<div style='text-align:center;'><img src='data:image/png;base64,{img_i}' width='100'></div>" if img_i else "📦", unsafe_allow_html=True)
        if st.button("📦 INVENTARIO", use_container_width=True): st.session_state.menu_principal = "Inventario"; st.rerun()
    with c3:
        st.markdown(f"<div style='text-align:center;'><img src='data:image/png;base64,{img_ing}' width='100'></div>" if img_ing else "💼", unsafe_allow_html=True)
        if st.button("💼 INGRESOS", use_container_width=True): st.session_state.menu_principal = "Ingresos"; st.rerun()
    with c4:
        st.markdown(f"<div style='text-align:center;'><img src='data:image/png;base64,{img_t}' width='100'></div>" if img_t else "💱", unsafe_allow_html=True)
        if st.button("💱 TASAS", use_container_width=True): st.session_state.menu_principal = "Tasas"; st.rerun()

    st.write("<br>", unsafe_allow_html=True)
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.markdown(f"<div style='text-align:center;'><img src='data:image/png;base64,{img_c}' width='100'></div>" if img_c else "🔒", unsafe_allow_html=True)
        if st.button("🔒 CIERRES", use_container_width=True): st.session_state.menu_principal = "Cierres"; st.rerun()
    with c6:
        st.markdown(f"<div style='text-align:center;'><img src='data:image/png;base64,{img_n}' width='100'></div>" if img_n else "👥", unsafe_allow_html=True)
        if st.button("👥 NÓMINA", use_container_width=True): st.session_state.menu_principal = "Nomina"; st.rerun()
    with c7:
        st.markdown(f"<div style='text-align:center;'><img src='data:image/png;base64,{img_seg}' width='100'></div>" if img_seg else "🔐", unsafe_allow_html=True)
        if st.button("🔐 SEGURIDAD", use_container_width=True): st.session_state.menu_principal = "Seguridad"; st.rerun()

# CARGA DE MÓDULOS
elif st.session_state.menu_principal == "Ventas": modulo_ventas.ejecutar()
elif st.session_state.menu_principal == "Inventario": modulo_inventario.ejecutar()
elif st.session_state.menu_principal == "Ingresos": modulo_ingresos.ejecutar() 
elif st.session_state.menu_principal == "Tasas": modulo_tasas.ejecutar()
elif st.session_state.menu_principal == "Cierres": modulo_cierres.ejecutar()
elif st.session_state.menu_principal == "Nomina": modulo_nomina.ejecutar()
elif st.session_state.menu_principal == "Seguridad": modulo_seguridad.ejecutar()