import streamlit as st
import pandas as pd
from datetime import datetime
from utilidades import cargar_json, guardar_json # CONEXIÓN A LA BÓVEDA SEGURA

# ==========================================
# 1. INICIALIZACIÓN DE DATOS
# ==========================================
def inicializar_estado():
    if 'tasa_bcv' not in st.session_state:
        st.session_state.tasa_bcv = 36.50
        
    # --- CARGA DESDE EL DISCO (BÓVEDA SEGURA) ---
    if 'fondos' not in st.session_state:
        st.session_state.fondos = cargar_json("fondos.json", {})
        
    # --- MIGRACIÓN FORZADA ---
    if "2. Productores (Nómina 50%)" in st.session_state.fondos:
        valor_guardado = st.session_state.fondos.pop("2. Productores (Nómina 50%)")
        st.session_state.fondos["2. Productores (Nómina 60%)"] = valor_guardado
        
    if "5. Utilidad Libre (Dueño/Compartir 20%)" in st.session_state.fondos:
        valor_guardado = st.session_state.fondos.pop("5. Utilidad Libre (Dueño/Compartir 20%)")
        st.session_state.fondos["5. Utilidad Libre (Dueño/Compartir 10%)"] = valor_guardado
        
    claves_necesarias = [
        "2. Productores (Nómina 60%)",
        "5. Utilidad Libre (Dueño/Compartir 10%)",
        "6. Subfondo Inasistencias (Bonos)"
    ]
    for clave in claves_necesarias:
        if clave not in st.session_state.fondos:
            st.session_state.fondos[clave] = 0.0
            
    # --- CARGA DESDE EL DISCO (BÓVEDA SEGURA) ---
    if 'db_trabajadores' not in st.session_state or len(st.session_state.db_trabajadores) == 0 or "Sueldo Semanal ($)" not in st.session_state.db_trabajadores[0]:
        st.session_state.db_trabajadores = cargar_json("trabajadores.json", [
            {"Nombre": "Panadero Principal", "Cargo": "Panadero", "Sueldo Semanal ($)": 18.0},
            {"Nombre": "Ayudante Panadería", "Cargo": "Ayudante", "Sueldo Semanal ($)": 15.0},
            {"Nombre": "Cajero/a 1", "Cargo": "Ventas", "Sueldo Semanal ($)": 14.0},
            {"Nombre": "Cajero/a 2", "Cargo": "Ventas", "Sueldo Semanal ($)": 14.0}
        ])
        
    if 'historial_nomina' not in st.session_state:
        st.session_state.historial_nomina = cargar_json("historial_nomina.json", [])
        
    if 'db_movimientos_fondos' not in st.session_state:
        st.session_state.db_movimientos_fondos = cargar_json("movimientos_fondos.json", [])

def aplicar_css():
    st.markdown("""
        <style>
        .tarjeta-trabajador {
            background-color: #f8f9fa; padding: 15px; border-radius: 10px; 
            border-left: 5px solid #4CAF50; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        }
        .monto-sugerido { font-size: 22px; font-weight: bold; color: #28a745; margin: 5px 0; }
        .fondo-global {
            background-color: #e8f5e9; border: 2px solid #28a745; padding: 20px; 
            border-radius: 10px; text-align: center; margin-bottom: 20px; height: 100%;
        }
        .subfondo-card {
            background-color: #fff3cd; border: 2px solid #ffc107; padding: 20px; 
            border-radius: 10px; text-align: center; margin-bottom: 20px; height: 100%;
        }
        .alerta-falta {
            background-color: #ffeeba; border: 2px solid #d39e00; padding: 20px; 
            border-radius: 10px; text-align: center; margin-bottom: 20px; height: 100%;
        }
        .btn-volver-arriba button {
            background-color: #f8f9fa !important; color: #dc3545 !important; 
            border: 2px solid #dc3545 !important; font-weight: bold;
        }
        .btn-volver-arriba button:hover {
            background-color: #dc3545 !important; color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. VISTAS DEL MÓDULO
# ==========================================
def mostrar_nomina():
    # --- BOTÓN DE VOLVER ARRIBA ---
    col_v1, col_v2 = st.columns([1, 4])
    with col_v1:
        st.markdown('<div class="btn-volver-arriba">', unsafe_allow_html=True)
        if st.button("⬅ VOLVER AL MENÚ", use_container_width=True):
            st.session_state.menu_principal = "Escritorio"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center; color: #2c3e50; margin-top: -20px;'>👥 NÓMINA Y PRODUCTORES</h1>", unsafe_allow_html=True)
    st.write("Control de pagos por Sueldo Base, prorrateo de días y gestión de inasistencias.")
    
    tasa = st.session_state.get('tasa_bcv', 36.50)
    llave_nomina = "2. Productores (Nómina 60%)"
    fondo_nomina_usd = st.session_state.fondos.get(llave_nomina, 0.0)
    subfondo_usd = st.session_state.fondos.get("6. Subfondo Inasistencias (Bonos)", 0.0)
    
    # --- CÁLCULO DE NÓMINA TOTAL Y LO QUE FALTA ---
    total_costo_nomina = sum(t.get("Sueldo Semanal ($)", 0.0) for t in st.session_state.db_trabajadores)
    faltante = total_costo_nomina - fondo_nomina_usd if total_costo_nomina > fondo_nomina_usd else 0.0
    
    col_top1, col_top2, col_top3 = st.columns(3)
    
    with col_top1:
        st.markdown(f"""
            <div class="fondo-global">
                <h4 style="margin:0; color: #155724;">Fondo Base (El Pote)</h4>
                <h1 style="margin:0; color: #1e7e34;">${fondo_nomina_usd:.2f} USD</h1>
            </div>
        """, unsafe_allow_html=True)
        
    with col_top2:
        if faltante > 0:
            st.markdown(f"""
                <div class="alerta-falta">
                    <h4 style="margin:0; color: #856404;">Costo Total Nómina: ${total_costo_nomina:.2f}</h4>
                    <h2 style="margin:0; color: #d39e00;">Faltan: ${faltante:.2f}</h2>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="fondo-global" style="background-color: #d4edda;">
                    <h4 style="margin:0; color: #155724;">Costo Total Nómina: ${total_costo_nomina:.2f}</h4>
                    <h2 style="margin:0; color: #1e7e34;">¡NÓMINA CUBIERTA!</h2>
                </div>
            """, unsafe_allow_html=True)
            
    with col_top3:
        st.markdown(f"""
            <div class="subfondo-card">
                <h4 style="margin:0; color: #856404;">Subfondo Inasistencias</h4>
                <h1 style="margin:0; color: #d39e00;">${subfondo_usd:.2f} USD</h1>
            </div>
        """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["⚙️ Equipo", "💸 Registrar Pago (Por Días)", "🔄 Repartir Inasistencias", "📋 Historial por Trabajador"])
    
    # ---------------- TAB 1: EQUIPO Y SUELDOS ----------------
    with tab1:
        st.write("### 🍰 Sueldos Base Semanales (7 días)")
        st.write("Estos son los montos que cobrará cada persona si asiste todos los días de la semana.")
        
        cols = st.columns(2)
        for i, trab in enumerate(st.session_state.db_trabajadores):
            sueldo_base = trab.get("Sueldo Semanal ($)", 0.0) 
            valor_dia = round(sueldo_base / 7, 2)
            
            with cols[i % 2]:
                st.markdown(f"""
                <div class="tarjeta-trabajador">
                    <h4 style="margin:0;">{trab['Nombre']} ({trab['Cargo']})</h4>
                    <p style="margin:0; color: #666;">Sueldo Base (7 días): <b>${sueldo_base:.2f}</b></p>
                    <p style="margin:0; color: #28a745;">Valor por día: <b>${valor_dia:.2f}</b></p>
                </div>
                """, unsafe_allow_html=True)
                
        with st.expander("🛠️ Configurar / Editar Sueldos o Trabajadores"):
            st.write("Modifica directamente en la tabla los nombres o el sueldo semanal en dólares de tu equipo.")
            df_edit = pd.DataFrame(st.session_state.db_trabajadores)
            df_editado = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True)
            
            if st.button("💾 Guardar Cambios en el Equipo", type="primary"):
                st.session_state.db_trabajadores = df_editado.to_dict('records')
                # --- GUARDADO PERMANENTE ---
                guardar_json("trabajadores.json", st.session_state.db_trabajadores)
                st.rerun()

    # ---------------- TAB 2: REGISTRAR PAGO (CÁLCULO EN VIVO) ----------------
    with tab2:
        st.write("### 📤 Pago Proporcional (Máximo 7 días)")
        
        nombres_trabajadores = [f"{t['Nombre']} ({t['Cargo']})" for t in st.session_state.db_trabajadores]
        
        col_p1, col_p2, col_p3 = st.columns(3)
        trabajador_sel = col_p1.selectbox("Trabajador a pagar:", nombres_trabajadores)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes_sel = col_p2.selectbox("Mes:", meses, index=datetime.now().month - 1)
        semana_sel = col_p3.selectbox("Semana:", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5"])
        
        st.write("#### Asistencia")
        col_d1, col_d2 = st.columns(2)
        
        dias_totales = col_d1.number_input("Días de la semana", min_value=7, max_value=7, value=7, disabled=True)
        dias_trabajados = col_d2.number_input("Días que realmente trabajó", min_value=0.0, max_value=7.0, value=7.0, step=0.5)
        
        sueldo_base = 0.0
        nombre_limpio = ""
        for t in st.session_state.db_trabajadores:
            if f"{t['Nombre']} ({t['Cargo']})" == trabajador_sel:
                sueldo_base = t.get("Sueldo Semanal ($)", 0.0)
                nombre_limpio = t.get("Nombre", "")
                break
        
        valor_dia_calc = round(sueldo_base / 7, 2)
        sugerido_proporcional = round(valor_dia_calc * dias_trabajados, 2)
        
        if dias_trabajados == 7.0:
            sugerido_proporcional = sueldo_base
            
        descuento = round(sueldo_base - sugerido_proporcional, 2)
        
        st.info(f"📋 **Cálculo:** ${valor_dia_calc:.2f} (por día) x {dias_trabajados} días = **${sugerido_proporcional:.2f}**.")
        
        enviar_subfondo = False
        if descuento > 0:
            st.warning(f"⚠️ Descuento por inasistencia: **${descuento:.2f}**")
            enviar_subfondo = st.checkbox("☑️ Guardar este descuento en el Subfondo de Inasistencias", value=True)
        
        valor_defecto = float(sugerido_proporcional) if sugerido_proporcional > 0 else 0.0
        monto_pagar_usd = st.number_input("Monto final a pagar en Dólares ($)", min_value=0.0, step=1.0, value=valor_defecto)
        
        if st.button("💸 PROCESAR PAGO", use_container_width=True, type="primary"):
            total_a_descontar_del_pote = monto_pagar_usd + (descuento if enviar_subfondo else 0.0)
            
            if monto_pagar_usd <= 0:
                st.error("El monto a pagar debe ser mayor a cero.")
            elif total_a_descontar_del_pote > fondo_nomina_usd:
                st.error(f"Fondos insuficientes en el Pote de Nómina para cubrir este pago.")
            else:
                st.session_state.fondos[llave_nomina] -= total_a_descontar_del_pote
                
                st.session_state.historial_nomina.append({
                    "Fecha de Pago": datetime.now().strftime('%Y-%m-%d %H:%M'),
                    "Trabajador": nombre_limpio,
                    "Mes": f"{mes_sel} {datetime.now().year}",
                    "Semana": semana_sel,
                    "Monto Pagado ($)": monto_pagar_usd,
                    "Equivalente (BS)": monto_pagar_usd * tasa
                })
                
                if 'db_movimientos_fondos' in st.session_state:
                    st.session_state.db_movimientos_fondos.append({
                        "Fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "Fondo": llave_nomina,
                        "Tipo": "EGRESO NÓMINA",
                        "Monto ($)": -monto_pagar_usd,
                        "Concepto": f"Pago a {nombre_limpio} ({dias_trabajados} días) - {semana_sel}"
                    })
                
                if enviar_subfondo and descuento > 0:
                    st.session_state.fondos["6. Subfondo Inasistencias (Bonos)"] += descuento
                    if 'db_movimientos_fondos' in st.session_state:
                        st.session_state.db_movimientos_fondos.append({
                            "Fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "Fondo": "6. Subfondo Inasistencias (Bonos)",
                            "Tipo": "INGRESO POR FALTA",
                            "Monto ($)": descuento,
                            "Concepto": f"Descuento a {nombre_limpio} por {7.0 - dias_trabajados} días no laborados"
                        })
                
                # --- GUARDADO PERMANENTE ---
                guardar_json("fondos.json", st.session_state.fondos)
                guardar_json("historial_nomina.json", st.session_state.historial_nomina)
                if 'db_movimientos_fondos' in st.session_state:
                    guardar_json("movimientos_fondos.json", st.session_state.db_movimientos_fondos)
                        
                if enviar_subfondo and descuento > 0:
                    st.success(f"Pago registrado y ${descuento:.2f} ahorrados en el Subfondo.")
                else:
                    st.success(f"¡Pago registrado exitosamente a {nombre_limpio}!")
                
                st.rerun()

    # ---------------- TAB 3: REPARTIR SUBFONDO (BONOS MULTIPLES) ----------------
    with tab3:
        st.write("### 🔄 Repartir el Subfondo de Inasistencias")
        st.write("Usa el dinero acumulado por faltas para bonificar a los que trabajaron extra o recupéralo a tu utilidad.")
        
        nombres_puros = [t.get('Nombre', 'Desconocido') for t in st.session_state.db_trabajadores]
        
        with st.form("form_repartir_subfondo"):
            st.info(f"💰 Saldo disponible para repartir: **${subfondo_usd:.2f}**")
            
            destino = st.radio("¿Qué deseas hacer con el Subfondo?", 
                               ["Repartirlo como BONO a trabajadores", "Enviarlo a mi Fondo de UTILIDAD LIBRE"])
            
            trabajadores_seleccionados = []
            if "BONO" in destino:
                trabajadores_seleccionados = st.multiselect("Selecciona los trabajadores que recibirán el bono:", nombres_puros)
            
            valor_max = float(subfondo_usd) if subfondo_usd > 0 else 0.0
            monto_repartir = st.number_input("Monto TOTAL a extraer del subfondo ($)", min_value=0.0, max_value=valor_max, step=1.0, value=valor_max)
            
            if st.form_submit_button("🔄 EJECUTAR REPARTICIÓN", use_container_width=True):
                if monto_repartir <= 0:
                    st.error("El monto debe ser mayor a cero.")
                elif monto_repartir > subfondo_usd + 0.01:
                    st.error("No hay fondos suficientes.")
                else:
                    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                    mes_str = f"{meses[datetime.now().month - 1]} {datetime.now().year}"
                    
                    if "BONO" in destino:
                        if not trabajadores_seleccionados:
                            st.error("Debes seleccionar al menos un trabajador para darle el bono.")
                        else:
                            st.session_state.fondos["6. Subfondo Inasistencias (Bonos)"] -= monto_repartir
                            monto_por_persona = round(monto_repartir / len(trabajadores_seleccionados), 2)
                            
                            for trab in trabajadores_seleccionados:
                                st.session_state.historial_nomina.append({
                                    "Fecha de Pago": datetime.now().strftime('%Y-%m-%d %H:%M'),
                                    "Trabajador": trab,
                                    "Mes": mes_str,
                                    "Semana": "Bono Extraordinario",
                                    "Monto Pagado ($)": monto_por_persona,
                                    "Equivalente (BS)": monto_por_persona * tasa
                                })
                                
                            if 'db_movimientos_fondos' in st.session_state:
                                st.session_state.db_movimientos_fondos.append({
                                    "Fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    "Fondo": "6. Subfondo Inasistencias (Bonos)",
                                    "Tipo": "EGRESO BONO",
                                    "Monto ($)": -monto_repartir,
                                    "Concepto": f"Bono repartido entre {len(trabajadores_seleccionados)} trabs."
                                })
                                
                            # --- GUARDADO PERMANENTE ---
                            guardar_json("fondos.json", st.session_state.fondos)
                            guardar_json("historial_nomina.json", st.session_state.historial_nomina)
                            if 'db_movimientos_fondos' in st.session_state:
                                guardar_json("movimientos_fondos.json", st.session_state.db_movimientos_fondos)
                                
                            st.success(f"¡Bono repartido! Se asignaron ${monto_por_persona:.2f} a cada seleccionado.")
                            st.rerun()
                    else:
                        st.session_state.fondos["6. Subfondo Inasistencias (Bonos)"] -= monto_repartir
                        st.session_state.fondos["5. Utilidad Libre (Dueño/Compartir 10%)"] += monto_repartir
                        
                        if 'db_movimientos_fondos' in st.session_state:
                            st.session_state.db_movimientos_fondos.append({
                                "Fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                "Fondo": "6. Subfondo Inasistencias (Bonos)",
                                "Tipo": "TRANSF. SALIDA",
                                "Monto ($)": -monto_repartir,
                                "Concepto": "Recuperado hacia Utilidad Libre"
                            })
                            st.session_state.db_movimientos_fondos.append({
                                "Fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                "Fondo": "5. Utilidad Libre (Dueño/Compartir 10%)",
                                "Tipo": "TRANSF. ENTRADA",
                                "Monto ($)": monto_repartir,
                                "Concepto": "Proveniente del Subfondo de Inasistencias"
                            })
                        
                        # --- GUARDADO PERMANENTE ---
                        guardar_json("fondos.json", st.session_state.fondos)
                        if 'db_movimientos_fondos' in st.session_state:
                            guardar_json("movimientos_fondos.json", st.session_state.db_movimientos_fondos)
                            
                        st.success(f"¡Dinero recuperado! ${monto_repartir:.2f} fueron a tu fondo de Utilidad.")
                        st.rerun()

    # ---------------- TAB 4: HISTORIAL Y REPORTES ----------------
    with tab4:
        st.write("### 📅 Reportes y Consolidado")
        
        if not st.session_state.historial_nomina:
            st.info("Aún no se han registrado pagos de nómina ni bonos.")
        else:
            df_nomina = pd.DataFrame(st.session_state.historial_nomina)
            
            col_f1, col_f2 = st.columns(2)
            meses_disponibles = sorted(list(df_nomina["Mes"].unique()))
            trabajadores_disponibles = sorted(list(df_nomina["Trabajador"].unique()))
            
            filtro_mes = col_f1.selectbox("Filtrar por Mes:", ["Todos los Meses"] + meses_disponibles)
            filtro_trab = col_f2.selectbox("Ver historial de:", ["Todos los Trabajadores"] + trabajadores_disponibles)
            
            if filtro_mes != "Todos los Meses":
                df_nomina = df_nomina[df_nomina["Mes"] == filtro_mes]
            if filtro_trab != "Todos los Trabajadores":
                df_nomina = df_nomina[df_nomina["Trabajador"] == filtro_trab]
                
            if not df_nomina.empty:
                st.write("#### 📊 Total Pagado Según los Filtros")
                total_filtrado = df_nomina["Monto Pagado ($)"].sum()
                st.markdown(f"<h2 style='color:#28a745;'>${total_filtrado:.2f} USD</h2>", unsafe_allow_html=True)
                
                st.write("#### 🧾 Detalle de Pagos (Base + Bonos)")
                st.dataframe(df_nomina.sort_values(by="Fecha de Pago", ascending=False), use_container_width=True, hide_index=True)
            else:
                st.warning("No hay pagos que coincidan con la búsqueda.")

# ==========================================
# 3. CONTROLADOR
# ==========================================
def ejecutar():
    inicializar_estado()
    aplicar_css()
    mostrar_nomina()

if __name__ == "__main__":
    ejecutar()