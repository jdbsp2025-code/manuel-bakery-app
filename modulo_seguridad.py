import streamlit as st
import pandas as pd
from utilidades import cargar_json, guardar_json # CONEXIÓN A LA BÓVEDA SEGURA

# ==========================================
# 1. INICIALIZACIÓN DE DATOS (DESDE DISCO)
# ==========================================
def inicializar_seguridad():
    if 'db_usuarios' not in st.session_state:
        # Si no hay archivo, creamos a Manuel como el Administrador por defecto
        st.session_state.db_usuarios = cargar_json("usuarios.json", [
            {"Nombre Completo": "Manuel", "Usuario (Login)": "admin", "Rol": "Administrador", "Estado": "Activo", "Clave": "1234"}
        ])

def ejecutar():
    inicializar_seguridad()
    
    # --- BOTÓN PARA REGRESAR ---
    if st.button("◀ Volver al Escritorio", type="secondary"):
        st.session_state.menu_principal = "Escritorio"
        st.rerun()

    st.markdown("---")
    st.markdown("<h2 style='text-align: center; color: #D35400;'>🔐 Gestión de Seguridad y Usuarios</h2>", unsafe_allow_html=True)
    st.write("")

    # Organizamos el módulo en 4 pestañas para incluir la edición completa
    tab1, tab2, tab3, tab4 = st.tabs(["👥 Lista de Usuarios", "➕ Nuevo Usuario", "✏️ Editar Datos", "🔑 Contraseñas"])

    # --- PESTAÑA 1: VER USUARIOS ---
    with tab1:
        st.subheader("Usuarios Registrados en COMUNAPP")
        st.info("Visualización de todos los empleados y sus accesos.")
        
        if st.session_state.db_usuarios:
            df_usuarios = pd.DataFrame(st.session_state.db_usuarios)
            # Ocultamos la columna de claves por seguridad visual
            if "Clave" in df_usuarios.columns:
                df_mostrar = df_usuarios.drop(columns=["Clave"])
            else:
                df_mostrar = df_usuarios
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        else:
            st.warning("No hay usuarios registrados en el sistema.")

    # --- PESTAÑA 2: CREAR USUARIO ---
    with tab2:
        st.subheader("Crear un Nuevo Acceso")
        with st.form("form_nuevo_usuario"):
            nombre_nuevo = st.text_input("Nombre Completo del Empleado", placeholder="Ej. Juan Pérez")
            login_nuevo = st.text_input("Nombre de Usuario (Login)", placeholder="Ej. juan.ventas")
            rol_nuevo = st.selectbox("Rol del Sistema", ["Ventas", "Producción", "Administrador"])
            clave_nueva = st.text_input("Contraseña Temporal", type="password")
            
            if st.form_submit_button("Guardar Usuario", type="primary"):
                if nombre_nuevo and login_nuevo and clave_nueva:
                    # Validar que el login no exista ya
                    logins_existentes = [u["Usuario (Login)"] for u in st.session_state.db_usuarios]
                    if login_nuevo in logins_existentes:
                        st.error("Ese nombre de usuario (Login) ya existe. Por favor elige otro.")
                    else:
                        st.session_state.db_usuarios.append({
                            "Nombre Completo": nombre_nuevo,
                            "Usuario (Login)": login_nuevo,
                            "Rol": rol_nuevo,
                            "Estado": "Activo",
                            "Clave": clave_nueva
                        })
                        # GUARDADO PERMANENTE
                        guardar_json("usuarios.json", st.session_state.db_usuarios)
                        st.success("✅ Usuario registrado con éxito y guardado permanentemente.")
                        st.rerun()
                else:
                    st.error("Por favor completa todos los campos.")

    # --- PESTAÑA 3: EDITAR USUARIO ---
    with tab3:
        st.subheader("Editar Datos de un Empleado")
        st.write("Selecciona un empleado para modificar su nombre, usuario de acceso, rol o estado.")
        
        if not st.session_state.db_usuarios:
            st.info("No hay usuarios para editar.")
        else:
            # Lista dinámica con los usuarios reales
            lista_logins = [u["Usuario (Login)"] for u in st.session_state.db_usuarios]
            usuario_a_editar = st.selectbox("Seleccionar Empleado a Editar:", lista_logins)
            
            # Buscar los datos del usuario seleccionado
            datos_actuales = next((u for u in st.session_state.db_usuarios if u["Usuario (Login)"] == usuario_a_editar), None)
            
            if datos_actuales:
                with st.form("form_editar_usuario"):
                    st.write(f"Editando los datos de: **{usuario_a_editar}**")
                    
                    edit_nombre = st.text_input("Nombre Completo", value=datos_actuales.get("Nombre Completo", ""))
                    edit_username = st.text_input("Usuario (Login) - El que usa para entrar", value=datos_actuales.get("Usuario (Login)", ""))
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        rol_idx = ["Ventas", "Producción", "Administrador"].index(datos_actuales.get("Rol", "Ventas")) if datos_actuales.get("Rol", "Ventas") in ["Ventas", "Producción", "Administrador"] else 0
                        edit_rol = st.selectbox("Rol", ["Ventas", "Producción", "Administrador"], index=rol_idx)
                    with col2:
                        est_idx = ["Activo", "Inactivo"].index(datos_actuales.get("Estado", "Activo")) if datos_actuales.get("Estado", "Activo") in ["Activo", "Inactivo"] else 0
                        edit_estado = st.selectbox("Estado en el sistema", ["Activo", "Inactivo"], index=est_idx)
                    
                    if st.form_submit_button("Actualizar Datos del Empleado", type="primary"):
                        # Validar si cambió el login y si el nuevo ya está ocupado por OTRO usuario
                        if edit_username != usuario_a_editar and edit_username in lista_logins:
                            st.error("El nuevo nombre de usuario ya está ocupado por otra persona.")
                        else:
                            datos_actuales["Nombre Completo"] = edit_nombre
                            datos_actuales["Usuario (Login)"] = edit_username
                            datos_actuales["Rol"] = edit_rol
                            datos_actuales["Estado"] = edit_estado
                            
                            # GUARDADO PERMANENTE
                            guardar_json("usuarios.json", st.session_state.db_usuarios)
                            st.success(f"✅ Los datos han sido actualizados. Ahora este empleado entrará con el usuario: '{edit_username}'")
                            st.rerun()

    # --- PESTAÑA 4: CAMBIAR CONTRASEÑA ---
    with tab4:
        st.subheader("Restablecer Contraseñas")
        st.write("Asigna una nueva contraseña si el empleado la olvidó.")
        
        if not st.session_state.db_usuarios:
            st.info("No hay usuarios registrados.")
        else:
            lista_logins_clave = [u["Usuario (Login)"] for u in st.session_state.db_usuarios]
            usuario_a_cambiar = st.selectbox("Seleccionar Empleado:", lista_logins_clave, key="select_clave")
            
            # Validación doble para evitar errores de tipeo al cambiar claves
            nueva_clave = st.text_input("Escriba la nueva contraseña:", type="password")
            confirma_clave = st.text_input("Confirme la nueva contraseña:", type="password")
            
            if st.button("Actualizar Clave de Acceso", type="primary"):
                if nueva_clave == "":
                    st.error("⛔ La contraseña no puede estar vacía.")
                elif nueva_clave != confirma_clave:
                    st.error("⛔ Las contraseñas no coinciden. Intente de nuevo.")
                else:
                    for u in st.session_state.db_usuarios:
                        if u["Usuario (Login)"] == usuario_a_cambiar:
                            u["Clave"] = nueva_clave
                            break
                            
                    # GUARDADO PERMANENTE
                    guardar_json("usuarios.json", st.session_state.db_usuarios)
                    st.success(f"✅ Contraseña de {usuario_a_cambiar} actualizada permanentemente.")