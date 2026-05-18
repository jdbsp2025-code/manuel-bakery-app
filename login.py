import streamlit as st
from utilidades import cargar_json # CONEXIÓN REAL A LA BÓVEDA

def mostrar_login():
    # --- DISEÑO VISUAL "ARTISAN BAKERY" ---
    st.markdown("""
        <style>
        /* Fondo crema suave para que resalte la limpieza */
        .stApp {
            background-color: #fdf5e6; 
        }
        
        /* Tarjeta de Login más elegante */
        .login-box {
            background: #ffffff;
            padding: 50px 40px;
            border-radius: 15px;
            box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.05);
            border-bottom: 5px solid #68A042; /* El verde de tu sistema */
            text-align: center;
        }

        /* Título con tipografía profesional */
        .main-title {
            color: #2c3e50;
            font-size: 42px;
            font-weight: 800;
            margin-bottom: 0px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .sub-title {
            color: #68A042;
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 3px;
            margin-bottom: 30px;
        }

        /* Inputs redondeados y limpios */
        div[data-testid="stTextInput"] input {
            border-radius: 8px !important;
            border: 1px solid #dcdcdc !important;
            padding: 10px !important;
        }

        /* Botón con degradado verde profesional */
        div[data-testid="stButton"] button {
            background: linear-gradient(135deg, #68A042 0%, #4a7c2f 100%) !important;
            color: white !important;
            border-radius: 8px !important;
            height: 50px !important;
            font-weight: bold !important;
            font-size: 18px !important;
            border: none !important;
            transition: 0.3s !important;
            margin-top: 20px;
        }
        div[data-testid="stButton"] button:hover {
            filter: brightness(1.1);
            transform: scale(1.02);
        }

        /* Estilo para el radio de turnos */
        div[role="radiogroup"] {
            background: #f9f9f9;
            padding: 10px;
            border-radius: 10px;
            border: 1px solid #eee;
        }
        </style>
    """, unsafe_allow_html=True)

    st.write("<br><br><br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.3, 1])

    with col2:
        st.markdown("""
            <div class="login-box">
                <div style="font-size: 50px; margin-bottom: 10px;">🥖</div>
                <div class="main-title">COMUNAPP</div>
                <div class="sub-title">Gestión de Panadería</div>
            </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.write("")
            usuario = st.text_input("👤 Usuario", placeholder="Nombre de acceso")
            clave = st.text_input("🔑 Contraseña", type="password", placeholder="••••••••")
            
            st.markdown("<p style='text-align: center; font-size: 13px; color: #777; margin-bottom: 5px;'>Seleccionar Turno de Trabajo:</p>", unsafe_allow_html=True)
            turno = st.radio("Turno", ["☀️ MAÑANA", "🌙 TARDE"], horizontal=True, label_visibility="collapsed")
            
            if st.button("ACCEDER AL PANEL", use_container_width=True):
                turno_real = "MAÑANA" if "MAÑANA" in turno else "TARDE"
                
                # --- VALIDACIÓN CON LA BÓVEDA SEGURA ---
                usuarios_db = cargar_json("usuarios.json", [
                    {"Usuario (Login)": "admin", "Clave": "1234", "Estado": "Activo", "Nombre Completo": "Administrador"}
                ])
                
                encontrado = False
                for u in usuarios_db:
                    if u.get("Usuario (Login)") == usuario and u.get("Clave") == clave:
                        if u.get("Estado", "Activo") == "Activo":
                            st.session_state.autenticado = True
                            st.session_state.usuario_actual = u.get("Nombre Completo", usuario)
                            st.session_state.turno_actual = f"TURNO {turno_real}"
                            st.rerun()
                        else:
                            st.error("⛔ Usuario inactivo.")
                            return
                        encontrado = True
                        break
                
                if not encontrado:
                    st.error("⛔ Credenciales incorrectas.")