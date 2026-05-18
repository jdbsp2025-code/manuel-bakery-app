import streamlit as st
import pandas as pd
from datetime import datetime
from utilidades import cargar_json, guardar_json

# ==========================================
# 1. INICIALIZACIÓN DE FONDOS Y MEMORIA
# ==========================================
def inicializar_estado():
    if 'tasa_bcv' not in st.session_state:
        st.session_state.tasa_bcv = 36.50
        
    if 'fondos' not in st.session_state:
        st.session_state.fondos = cargar_json("fondos.json", {})
        
    if 'respaldo_detalles' not in st.session_state:
        st.session_state.respaldo_detalles = cargar_json("respaldo_detalles.json", {
            "Dólares Físicos": 0.0,
            "Bolívares Físicos": 0.0,
            "Cuenta Bicentenario": 0.0
        })
        
    if "2. Productores (Nómina 50%)" in st.session_state.fondos:
        valor_guardado = st.session_state.fondos.pop("2. Productores (Nómina 50%)")
        st.session_state.fondos["2. Productores (Nómina 60%)"] = valor_guardado
        
    if "5. Utilidad Libre (Dueño/Compartir 20%)" in st.session_state.fondos:
        valor_guardado = st.session_state.fondos.pop("5. Utilidad Libre (Dueño/Compartir 20%)")
        st.session_state.fondos["5. Utilidad Libre (Dueño/Compartir 10%)"] = valor_guardado
        
    claves_necesarias = [
        "1. Materia Prima (Reposición)",
        "2. Productores (Nómina 60%)",
        "3. Gastos Operativos (Transp/Internet 20%)",
        "4. Mantenimiento y Papelería (10%)",
        "5. Utilidad Libre (Dueño/Compartir 10%)",
        "6. Subfondo Inasistencias (Bonos)",
        "7. CAJA DE RESPALDO"
    ]
    
    for clave in claves_necesarias:
        if clave not in st.session_state.fondos:
            st.session_state.fondos[clave] = 0.0
            
    actualizar_total_respaldo()
            
    if 'db_movimientos_fondos' not in st.session_state:
        st.session_state.db_movimientos_fondos = cargar_json("movimientos_fondos.json", [])
        
    if 'historial_cierres' not in st.session_state:
        st.session_state.historial_cierres = cargar_json("historial_cierres.json", [])

    if 'db_almacen' not in st.session_state:
        st.session_state.db_almacen = cargar_json("almacen.json", {})
        
    if 'db_recetas_fijas' not in st.session_state:
        st.session_state.db_recetas_fijas = cargar_json("recetas.json", {})

def actualizar_total_respaldo():
    tasa = st.session_state.get('tasa_bcv', 36.50)
    total_usd = st.session_state.respaldo_detalles["Dólares Físicos"] + \
                (st.session_state.respaldo_detalles["Bolívares Físicos"] / tasa) + \
                (st.session_state.respaldo_detalles["Cuenta Bicentenario"] / tasa)
    st.session_state.fondos["7. CAJA DE RESPALDO"] = total_usd

def registrar_movimiento(fondo, tipo, monto, concepto, fecha_exacta=None, monto_original=None, moneda="USD"):
    if not fecha_exacta: 
        fecha_exacta = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
    if monto_original is None:
        monto_original = monto
        
    st.session_state.db_movimientos_fondos.append({
        "Fecha": fecha_exacta,
        "Fondo": fondo,
        "Tipo": tipo,
        "Monto ($)": monto,
        "Monto Original": monto_original,
        "Moneda": moneda,
        "Concepto": concepto
    })
    guardar_json("movimientos_fondos.json", st.session_state.db_movimientos_fondos)

def deshacer_operacion(fecha_buscar):
    """Motor universal que revierte matemáticamente cualquier operación por su fecha"""
    movs_a_mantener = []
    for mov in st.session_state.db_movimientos_fondos:
        if mov['Fecha'] == fecha_buscar:
            fondo = mov['Fondo']
            tipo = mov['Tipo']
            monto_usd = mov.get('Monto ($)', 0)
            monto_orig = mov.get('Monto Original', monto_usd)
            moneda = mov.get('Moneda', 'USD')
            
            # 1. Si el movimiento afectó la Caja de Respaldo
            if fondo == "7. CAJA DE RESPALDO":
                if moneda not in st.session_state.respaldo_detalles:
                    moneda = 'Dólares Físicos'
                
                # Al eliminar, hacemos la operación matemática contraria
                if tipo == "INGRESO" or "ENTRADA" in tipo:
                    st.session_state.respaldo_detalles[moneda] -= monto_orig
                elif tipo == "RETIRO" or "SALIDA" in tipo:
                    st.session_state.respaldo_detalles[moneda] += abs(monto_orig)
            
            # 2. Si el movimiento afectó una Alcancía Operativa
            else:
                if fondo in st.session_state.fondos:
                    if tipo == "INGRESO" or "ENTRADA" in tipo:
                        st.session_state.fondos[fondo] -= monto_usd
                    elif tipo == "EGRESO" or "SALIDA" in tipo:
                        st.session_state.fondos[fondo] += abs(monto_usd)
        else:
            movs_a_mantener.append(mov)
            
    st.session_state.db_movimientos_fondos = movs_a_mantener
    actualizar_total_respaldo()
    guardar_json("fondos.json", st.session_state.fondos)
    guardar_json("respaldo_detalles.json", st.session_state.respaldo_detalles)
    guardar_json("movimientos_fondos.json", st.session_state.db_movimientos_fondos)

def preparar_dataframe_movimientos():
    df_movs = pd.DataFrame(st.session_state.db_movimientos_fondos)
    if not df_movs.empty:
        if 'Monto Original' not in df_movs.columns:
            df_movs['Monto Original'] = df_movs['Monto ($)']
        if 'Moneda' not in df_movs.columns:
            df_movs['Moneda'] = 'USD'
        df_movs['Monto Original'] = df_movs['Monto Original'].fillna(df_movs['Monto ($)'])
        df_movs['Moneda'] = df_movs['Moneda'].fillna('USD')
    return df_movs

def aplicar_css():
    st.markdown("""
        <style>
        .fondo-card { padding: 20px; border-radius: 12px; color: white; text-align: center; box-shadow: 3px 3px 10px rgba(0,0,0,0.15); margin-bottom: 20px; min-height: 120px; }
        .f-mp { background: linear-gradient(135deg, #FF9800, #F57C00); }
        .f-prod { background: linear-gradient(135deg, #4CAF50, #388E3C); }
        .f-op { background: linear-gradient(135deg, #2196F3, #1976D2); }
        .f-mant { background: linear-gradient(135deg, #9C27B0, #7B1FA2); }
        .f-util { background: linear-gradient(135deg, #f44336, #d32f2f); }
        .f-respaldo { background: linear-gradient(135deg, #607D8B, #455A64); }
        .monto-usd { font-size: 30px; font-weight: bold; margin: 10px 0 0 0; }
        .monto-bs { font-size: 16px; margin: 0; opacity: 0.9; }
        .caja-exportacion { padding: 15px; border-radius: 8px; border: 1px solid #b8daff; background-color: #cce5ff; margin-top: 15px; }
        .metric-caja { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #dee2e6; text-align: center;}
        </style>
    """, unsafe_allow_html=True)

def generar_botones_exportacion(df_exportar, titulo_reporte, nombre_archivo, key_prefix):
    st.markdown("<div class='caja-exportacion'>", unsafe_allow_html=True)
    st.write(f"##### 🖨️ Exportar {titulo_reporte}")
    col1, col2 = st.columns(2)
    csv = df_exportar.to_csv(index=False).encode('utf-8')
    col1.download_button(label="📥 Descargar en Excel (CSV)", data=csv, file_name=f"{nombre_archivo}.csv", mime="text/csv", key=f"csv_{key_prefix}", use_container_width=True)
    html_table = df_exportar.to_html(index=False, justify="center")
    html_template = f"<html><head><title>{titulo_reporte}</title><style>body {{ font-family: Arial; padding: 20px; }} h1 {{ text-align: center; color: #2c3e50; border-bottom: 2px solid #28a745; }} table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }} th, td {{ border: 1px solid #ccc; padding: 10px; text-align: center; }} th {{ background-color: #f2f2f2; }}</style></head><body onload='window.print()'><h1>{titulo_reporte} - COMUNAPP</h1><p><strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>{html_table}</body></html>"
    col2.download_button(label="📄 Descargar para Imprimir (PDF)", data=html_template, file_name=f"{nombre_archivo}.html", mime="text/html", key=f"pdf_{key_prefix}", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 2. VISTAS DEL MÓDULO
# ==========================================
def mostrar_ingresos_egresos():
    st.markdown("<h1 style='text-align: center; color: #2c3e50;'>💼 INGRESOS Y EGRESOS (FONDOS)</h1>", unsafe_allow_html=True)
    
    tasa = st.session_state.get('tasa_bcv', 36.50)
    actualizar_total_respaldo() # Asegurar sincronización
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["💰 Estado de Fondos", "📥 Procesar Cierres", "📤 Gastar / Transferir", "📈 Resumen por Fondo", "⚖️ Comparación ING/EGR", "🏦 Caja de Respaldo"])
    
    # ---------------- TAB 1: ESTADO DE FONDOS ----------------
    with tab1:
        st.write("### 💵 Disponibilidad en Tiempo Real")
        c1, c2, c3 = st.columns(3)
        c4, c5, c6 = st.columns(3)
        columnas = [c1, c2, c3, c4, c5, c6]
        clases_css = ["f-mp", "f-prod", "f-op", "f-mant", "f-util", "f-respaldo"]
        
        fondos_principales = {k:v for k,v in st.session_state.fondos.items() if "Subfondo" not in k}
        datos_estado = []
        
        for i, (nombre_fondo, monto_usd) in enumerate(fondos_principales.items()):
            monto_bs = monto_usd * tasa
            datos_estado.append({"Nombre del Fondo": nombre_fondo, "Monto Físico ($)": round(monto_usd, 2), "Equivalente (BS)": round(monto_bs, 2)})
            with columnas[i]:
                st.markdown(f"<div class='fondo-card {clases_css[i]}'><h4 style='margin:0; font-size:14px;'>{nombre_fondo}</h4><p class='monto-usd'>${monto_usd:.2f}</p><p class='monto-bs'>Eq: {monto_bs:.2f} BS</p></div>", unsafe_allow_html=True)
                
        total_usd = sum(st.session_state.fondos.values())
        total_bs = total_usd * tasa
        datos_estado.append({"Nombre del Fondo": "TOTAL LIQUIDEZ GLOBAL", "Monto Físico ($)": round(total_usd, 2), "Equivalente (BS)": round(total_bs, 2)})
        
        c7, c8, c9 = st.columns([1, 2, 1])
        with c8:
            st.markdown(f"<div style='border: 3px dashed #28a745; padding: 20px; border-radius: 12px; text-align: center;'><h4 style='color: #28a745; margin:0;'>TOTAL LIQUIDEZ GENERAL</h4><p style='font-size: 32px; font-weight: bold; color: #28a745; margin: 10px 0 0 0;'>${total_usd:.2f}</p><p style='font-size: 16px; color: #555; margin: 0;'>{total_bs:.2f} BS</p></div>", unsafe_allow_html=True)
            
        st.markdown("---")
        generar_botones_exportacion(pd.DataFrame(datos_estado), "Estado Actual de Fondos", "Estado_Fondos", "tab1")

    # ---------------- TAB 2: PROCESAR CIERRES ----------------
    with tab2:
        st.write("### 📥 Distribución Inteligente de Cierres")
        
        # Obtenemos TODOS los cierres pendientes
        cierres_pendientes_todos = [c for c in st.session_state.historial_cierres if not c.get("distribuido", False)]
        
        if not cierres_pendientes_todos:
            st.info("✅ Todos los cierres de caja ya han sido procesados y distribuidos en sus fondos.")
        else:
            st.warning(f"Tienes **{len(cierres_pendientes_todos)} cierre(s)** de caja en total esperando para ser distribuidos.")
            
            # Extraer las fechas únicas de los cierres pendientes
            fechas_pendientes = sorted(list(set([c.get("fecha", "Sin fecha") for c in cierres_pendientes_todos])))
            
            col_sel1, col_sel2 = st.columns([2, 1])
            
            # Selector de fechas a procesar
            fechas_seleccionadas = col_sel1.multiselect(
                "📅 Selecciona la(s) fecha(s) que deseas procesar:", 
                fechas_pendientes, 
                default=fechas_pendientes
            )
            
            # BOTÓN MÁGICO PARA COMPROBAR/ACTUALIZAR SI EDITARON ALGO EN EL OTRO MÓDULO
            if col_sel2.button("🔄 Comprobar / Actualizar Análisis", use_container_width=True):
                # Forzamos la lectura fresca de los JSON desde el disco duro
                st.session_state.historial_cierres = cargar_json("historial_cierres.json", [])
                st.session_state.db_recetas_fijas = cargar_json("recetas.json", {})
                st.session_state.db_almacen = cargar_json("almacen.json", {})
                st.rerun()

            # Filtramos los cierres que el usuario realmente seleccionó
            cierres_a_procesar = [c for c in cierres_pendientes_todos if c.get("fecha", "Sin fecha") in fechas_seleccionadas]

            if not cierres_a_procesar:
                st.info("Selecciona al menos una fecha para ver el análisis de distribución.")
            else:
                venta_total_bs, costo_total_usd = 0.0, 0.0
                
                for cierre in cierres_a_procesar:
                    venta_total_bs += float(cierre.get("total_bs", 0.0))
                    
                    for prod_vendido in cierre.get("productos", []):
                        nombre_prod = prod_vendido.get("Producto")
                        cant_vendida = prod_vendido.get("Cant", 0)
                        
                        if 'db_recetas_fijas' in st.session_state and nombre_prod in st.session_state.db_recetas_fijas:
                            receta = st.session_state.db_recetas_fijas[nombre_prod]
                            
                            # Cálculo blindado y seguro contra campos faltantes
                            c_tanda = 0.0
                            for ing in receta.get("ingredientes", []):
                                n_ing = ing.get("ing")
                                cant_ing = ing.get("cant", 0)
                                if n_ing in st.session_state.db_almacen:
                                    datos_alm = st.session_state.db_almacen[n_ing]
                                    costo_u = datos_alm.get("Costo USD", 0.0)
                                    cant_b = max(1, datos_alm.get("Cantidad Base", 1.0))
                                    c_tanda += cant_ing * (costo_u / cant_b)
                                    
                            rendimiento = max(1, receta.get("rendimiento_tanda", 1))
                            unidades_empaque = receta.get("unidades_bolsa", 1)
                            
                            costo_empaque = (c_tanda / rendimiento) * unidades_empaque
                            costo_total_usd += (costo_empaque * cant_vendida)
                
                venta_total_usd = venta_total_bs / tasa
                ganancia_neta = venta_total_usd - costo_total_usd
                
                st.markdown(f"<div style='background-color:#f1f8ff; padding:20px; border-radius:10px; border:1px solid #cce5ff;'><h4>Análisis Automático de los Cierres Seleccionados:</h4><ul><li><b>Venta Bruta Recaudada:</b> ${venta_total_usd:.2f} <i>({venta_total_bs:.2f} BS)</i></li><li><b>Costo de Materia Prima a Recuperar:</b> ${costo_total_usd:.2f}</li><li><b style='color:green;'>Ganancia Limpia a Repartir: ${ganancia_neta:.2f}</b></li></ul></div><br>", unsafe_allow_html=True)
                
                if st.button("⚙️ DISTRIBUIR FONDOS AHORA", type="primary", use_container_width=True):
                    if ganancia_neta > 0:
                        reparto = {
                            "1. Materia Prima (Reposición)": costo_total_usd,
                            "2. Productores (Nómina 60%)": ganancia_neta * 0.60,
                            "3. Gastos Operativos (Transp/Internet 20%)": ganancia_neta * 0.20,
                            "4. Mantenimiento y Papelería (10%)": ganancia_neta * 0.10,
                            "5. Utilidad Libre (Dueño/Compartir 10%)": ganancia_neta * 0.10
                        }
                        fecha_dist = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Generar texto de concepto amigable
                        if len(fechas_seleccionadas) == 1:
                            texto_fechas = fechas_seleccionadas[0]
                        elif len(fechas_seleccionadas) <= 3:
                            texto_fechas = ", ".join(fechas_seleccionadas)
                        else:
                            texto_fechas = f"{len(fechas_seleccionadas)} días juntos"
                            
                        concepto_desc = f"Cierre de Ventas ({texto_fechas})"
                        
                        for fondo, monto in reparto.items():
                            st.session_state.fondos[fondo] += monto
                            registrar_movimiento(fondo, "INGRESO", monto, concepto_desc, fecha_exacta=fecha_dist)
                            
                        # Marcar SOLO los cierres de las fechas que eligió el usuario
                        for c in st.session_state.historial_cierres:
                            if not c.get("distribuido", False) and c.get("fecha", "Sin fecha") in fechas_seleccionadas:
                                c["distribuido"] = True
                                c["fecha_distribucion"] = fecha_dist
                                
                        guardar_json("fondos.json", st.session_state.fondos)
                        guardar_json("historial_cierres.json", st.session_state.historial_cierres)
                        st.success(f"¡Fondos de {texto_fechas} distribuidos exitosamente!")
                        st.rerun()
                    else:
                        st.error("Atención: El costo de producción fue mayor que la venta en las fechas seleccionadas. No hay ganancia a repartir.")
        
        st.markdown("---")
        st.write("#### 🧾 Historial de Cierres (Ingresos Procesados)")
        df_movs = preparar_dataframe_movimientos()
        if not df_movs.empty:
            # Filtramos todos los ingresos que provengan de un Cierre
            df_ingresos = df_movs[(df_movs['Tipo'] == "INGRESO") & (df_movs['Concepto'].str.contains("Cierre de Ventas"))].copy()
            if not df_ingresos.empty:
                df_agrupado = df_ingresos.groupby(["Fecha", "Concepto"])["Monto ($)"].sum().reset_index().rename(columns={"Monto ($)": "Ingreso Total Distribuido ($)"}).sort_values(by="Fecha", ascending=False)
                st.dataframe(df_agrupado, use_container_width=True, hide_index=True)
                
                generar_botones_exportacion(df_agrupado, "Historial de Cierres Procesados", "Cierres_Procesados", "tab2")
                
                st.markdown("<div style='padding: 15px; border-radius: 8px; border: 1px solid #f5c6cb; background-color: #f8d7da; margin-top: 15px;'>", unsafe_allow_html=True)
                st.write("##### 🗑️ Eliminar Distribución de Cierre")
                st.write("Al eliminar, se anulará la distribución de este cierre y el dinero se descontará de los fondos (volviendo al estado Pendiente).")
                opciones_c = [f"{row['Fecha']} | {row['Concepto']}" for idx, row in df_agrupado.iterrows()]
                cierre_a_borrar = st.selectbox("Seleccione la fecha y hora de la distribución a eliminar:", opciones_c)
                
                if st.button("🗑️ ELIMINAR DISTRIBUCIÓN", type="primary"):
                    if cierre_a_borrar:
                        fecha_buscar = cierre_a_borrar.split(" | ")[0]
                        deshacer_operacion(fecha_buscar)
                        for c in st.session_state.historial_cierres:
                            if c.get("fecha_distribucion") == fecha_buscar:
                                c["distribuido"] = False
                                c["fecha_distribucion"] = None
                        guardar_json("historial_cierres.json", st.session_state.historial_cierres)
                        st.success(f"¡Distribución eliminada exitosamente! Los cierres volvieron a estar Pendientes.")
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("Aún no se han procesado ingresos de cierres.")
        else:
            st.info("Aún no se han procesado ingresos de cierres.")

    # ---------------- TAB 3: GASTAR O TRANSFERIR (EXCLUYE RESPALDO) ----------------
    with tab3:
        st.write("### 📤 Operaciones Operativas")
        st.warning("⚠️ Nota: Las inyecciones a la Caja de Respaldo se administran desde su propia pestaña (Tab 6).")
        
        fondos_operativos = [k for k in st.session_state.fondos.keys()] 
        opcion_operacion = st.radio("¿Qué deseas hacer?", ["Registrar un Gasto (Bolívares)", "Transferir dinero entre fondos"], horizontal=True)
        
        if "Gasto" in opcion_operacion:
            fondo_sel = st.selectbox("¿De qué fondo vas a pagar?", [k for k in fondos_operativos if k != "7. CAJA DE RESPALDO"]) 
            saldo_disp_usd = st.session_state.fondos[fondo_sel]
            saldo_disp_bs = saldo_disp_usd * tasa
            
            st.info(f"💰 Saldo disponible en caja: **${saldo_disp_usd:.2f}  (Equivalente: {saldo_disp_bs:.2f} BS)**")
            
            with st.form("form_egreso"):
                concepto = st.text_input("Concepto del pago")
                # AQUI SE PIDE ESTRICTAMENTE EN BOLIVARES
                monto_retirar_bs = st.number_input("Monto a extraer (BS)", min_value=0.01, step=1.0)
                
                if st.form_submit_button("💸 REGISTRAR PAGO/EGRESO", use_container_width=True):
                    monto_retirar_usd = monto_retirar_bs / tasa
                    
                    if monto_retirar_usd > saldo_disp_usd:
                        st.error("Fondos insuficientes.")
                    elif concepto:
                        st.session_state.fondos[fondo_sel] -= monto_retirar_usd
                        # Se registra el monto original en BS
                        registrar_movimiento(fondo_sel, "EGRESO", -monto_retirar_usd, concepto, monto_original=-monto_retirar_bs, moneda="BS")
                        guardar_json("fondos.json", st.session_state.fondos)
                        st.success("Pago registrado correctamente.")
                        st.rerun()
                    else:
                        st.error("Escribe un concepto.")
            
            st.markdown("---")
            st.write("#### 📜 Historial Detallado de Egresos (Gastos en Bolívares)")
            df_movs = preparar_dataframe_movimientos()
            if not df_movs.empty:
                df_egresos = df_movs[df_movs['Tipo'] == "EGRESO"].copy()
                if not df_egresos.empty:
                    df_egresos['Fecha_DT'] = pd.to_datetime(df_egresos['Fecha'])
                    df_egresos['Mes'] = df_egresos['Fecha_DT'].dt.strftime('%B %Y')
                    df_egresos['Semana'] = df_egresos['Fecha_DT'].apply(lambda x: f"Semana {((x.day - 1) // 7) + 1}")
                    
                    # Mostramos el Monto Original (BS)
                    df_egresos_mostrar = df_egresos[["Mes", "Semana", "Fecha", "Fondo", "Concepto", "Monto Original", "Moneda"]].sort_values(by="Fecha", ascending=False)
                    st.dataframe(df_egresos_mostrar, use_container_width=True, hide_index=True)
                    
                    generar_botones_exportacion(df_egresos_mostrar, "Reporte de Egresos Generales", "Egresos", "tab3_egreso")
                    
                    st.markdown("<div style='padding: 15px; border-radius: 8px; border: 1px solid #f5c6cb; background-color: #f8d7da; margin-top: 15px;'>", unsafe_allow_html=True)
                    st.write("##### 🗑️ Eliminar Gasto")
                    st.write("Al eliminar el gasto, desaparece del historial y el dinero se devuelve al fondo.")
                    opciones_borrar = [f"{row['Fecha']} | {row['Concepto']} | {abs(row['Monto Original']):.2f} {row['Moneda']}" for idx, row in df_egresos.sort_values(by="Fecha", ascending=False).iterrows()]
                    egreso_a_borrar = st.selectbox("Seleccione el gasto a eliminar:", opciones_borrar)
                    
                    if st.button("🗑️ ELIMINAR GASTO", type="primary"):
                        if egreso_a_borrar:
                            fecha_buscar = egreso_a_borrar.split(" | ")[0]
                            deshacer_operacion(fecha_buscar)
                            st.success("¡Gasto eliminado permanentemente!")
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.info("Aún no se han registrado gastos.")
            else:
                st.info("Aún no se han registrado gastos.")
                        
        else: # TRANSFERENCIA 
            col_t1, col_t2 = st.columns(2)
            f_origen = col_t1.selectbox("Sacar dinero de:", fondos_operativos, key="f_origen")
            f_destino = col_t2.selectbox("Y meterlo en:", fondos_operativos, key="f_destino")
            
            moneda_origen = "USD"
            moneda_destino = "USD"
            
            # --- SUB-MENÚ INTELIGENTE ORIGEN ---
            if f_origen == "7. CAJA DE RESPALDO":
                moneda_origen = st.selectbox("¿Qué moneda vas a extraer de la Caja de Respaldo?", ["Dólares Físicos", "Bolívares Físicos", "Cuenta Bicentenario"])
                saldo_disp = st.session_state.respaldo_detalles[moneda_origen]
                simbolo = "$" if moneda_origen == "Dólares Físicos" else "BS"
                st.info(f"💰 Saldo disponible en ({moneda_origen}): **{simbolo} {saldo_disp:.2f}**")
                label_monto = f"Monto a transferir (En {moneda_origen})"
            else:
                saldo_disp = st.session_state.fondos[f_origen]
                st.info(f"💰 Saldo disponible en el origen: **${saldo_disp:.2f} USD**")
                label_monto = "Monto a transferir ($ USD)"
                
            # --- SUB-MENÚ INTELIGENTE DESTINO ---
            if f_destino == "7. CAJA DE RESPALDO":
                moneda_destino = st.selectbox("¿En qué cuenta lo vas a depositar dentro de la Caja de Respaldo?", ["Dólares Físicos", "Bolívares Físicos", "Cuenta Bicentenario"])
            
            with st.form("form_transferencia"):
                monto_tr = st.number_input(label_monto, min_value=0.01, step=1.0)
                motivo_t = st.text_input("Motivo de la transferencia")
                
                if st.form_submit_button("🔄 EJECUTAR TRANSFERENCIA", use_container_width=True):
                    if f_origen == f_destino and (f_origen != "7. CAJA DE RESPALDO" or (f_origen == "7. CAJA DE RESPALDO" and moneda_origen == moneda_destino)):
                        st.error("Debes seleccionar fondos (o monedas) distintos.")
                    elif monto_tr > saldo_disp:
                        st.error("No hay suficiente dinero en el origen seleccionado.")
                    elif motivo_t:
                        # 1. Convertir a Dólares Base para poder hacer la matemática si mezclan monedas
                        if f_origen == "7. CAJA DE RESPALDO" and moneda_origen != "Dólares Físicos":
                            monto_usd_base = monto_tr / tasa
                        else:
                            monto_usd_base = monto_tr
                            
                        # 2. Descontar del origen
                        if f_origen == "7. CAJA DE RESPALDO":
                            st.session_state.respaldo_detalles[moneda_origen] -= monto_tr
                        else:
                            st.session_state.fondos[f_origen] -= monto_usd_base
                            
                        # 3. Sumar al destino
                        if f_destino == "7. CAJA DE RESPALDO":
                            monto_final = monto_usd_base if moneda_destino == "Dólares Físicos" else (monto_usd_base * tasa)
                            st.session_state.respaldo_detalles[moneda_destino] += monto_final
                        else:
                            st.session_state.fondos[f_destino] += monto_usd_base
                            
                        fecha_op = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        # GUARDAR HISTORIAL SALIDA
                        registrar_movimiento(f_origen, "TRANSF. SALIDA", -monto_usd_base, f"A {f_destino} ({motivo_t})", fecha_exacta=fecha_op, monto_original=-monto_tr, moneda=moneda_origen)
                        
                        # GUARDAR HISTORIAL ENTRADA
                        monto_orig_dest = monto_usd_base if f_destino != "7. CAJA DE RESPALDO" else (monto_usd_base if moneda_destino == "Dólares Físicos" else (monto_usd_base * tasa))
                        moneda_dest_final = "USD" if f_destino != "7. CAJA DE RESPALDO" else moneda_destino
                        registrar_movimiento(f_destino, "TRANSF. ENTRADA", monto_usd_base, f"De {f_origen} ({motivo_t})", fecha_exacta=fecha_op, monto_original=monto_orig_dest, moneda=moneda_dest_final)
                        
                        guardar_json("respaldo_detalles.json", st.session_state.respaldo_detalles)
                        actualizar_total_respaldo()
                        guardar_json("fondos.json", st.session_state.fondos)
                        st.success("¡Transferencia realizada con éxito!")
                        st.rerun()
                    else:
                        st.error("Escribe un motivo.")
                        
            st.markdown("---")
            st.write("#### 📜 Historial de Transferencias Realizadas")
            df_movs = preparar_dataframe_movimientos()
            if not df_movs.empty:
                df_transf = df_movs[df_movs['Tipo'].str.contains("TRANSF")].copy()
                if not df_transf.empty:
                    df_transf['Fecha_DT'] = pd.to_datetime(df_transf['Fecha'])
                    df_transf['Mes'] = df_transf['Fecha_DT'].dt.strftime('%B %Y')
                    df_transf['Semana'] = df_transf['Fecha_DT'].apply(lambda x: f"Semana {((x.day - 1) // 7) + 1}")
                    df_t_mostrar = df_transf[["Mes", "Semana", "Fecha", "Fondo", "Tipo", "Concepto", "Monto Original", "Moneda"]].sort_values(by="Fecha", ascending=False)
                    st.dataframe(df_t_mostrar, use_container_width=True, hide_index=True)
                    
                    st.markdown("<div style='padding: 15px; border-radius: 8px; border: 1px solid #ffeeba; background-color: #fff3cd; margin-top: 15px;'>", unsafe_allow_html=True)
                    st.write("##### 🗑️ Eliminar Transferencia")
                    st.write("Al eliminar, se anula el movimiento y los fondos regresan a donde estaban originalmente.")
                    opciones_t = [f"{row['Fecha']} | {row['Concepto']} | {abs(row['Monto Original']):.2f} {row['Moneda']}" for idx, row in df_transf[df_transf['Tipo'] == 'TRANSF. SALIDA'].sort_values(by="Fecha", ascending=False).iterrows()]
                    t_a_borrar = st.selectbox("Seleccione la transferencia a eliminar:", opciones_t)
                    
                    if st.button("🗑️ ELIMINAR TRANSFERENCIA", type="primary"):
                        if t_a_borrar:
                            fecha_buscar = t_a_borrar.split(" | ")[0]
                            deshacer_operacion(fecha_buscar)
                            st.success("¡Transferencia eliminada permanentemente!")
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.info("Aún no se han realizado transferencias.")
            else:
                st.info("Aún no se han realizado transferencias.")

    # ---------------- TAB 4: RESUMEN POR FONDO ----------------
    with tab4:
        st.write("### 📈 Resumen Financiero por Fondo")
        fondo_filtro = st.selectbox("Seleccione el Fondo a analizar:", list(st.session_state.fondos.keys()))
        df_movs = preparar_dataframe_movimientos()
        if not df_movs.empty:
            df_fondo = df_movs[df_movs["Fondo"] == fondo_filtro].copy()
            if not df_fondo.empty:
                df_fondo['Fecha_DT'] = pd.to_datetime(df_fondo['Fecha'])
                df_fondo['Mes'] = df_fondo['Fecha_DT'].dt.strftime('%B %Y') 
                df_fondo['Semana'] = df_fondo['Fecha_DT'].apply(lambda x: f"Semana {((x.day - 1) // 7) + 1}")
                
                df_fondo['Ingresos ($)'] = df_fondo['Monto ($)'].apply(lambda x: x if x > 0 else 0)
                df_fondo['Gastos ($)'] = df_fondo['Monto ($)'].apply(lambda x: abs(x) if x < 0 else 0)
                
                tabla_resumen = df_fondo.groupby(['Mes', 'Semana'])[['Ingresos ($)', 'Gastos ($)']].sum().reset_index()
                tabla_resumen['Ahorro/Neto Semanal ($)'] = tabla_resumen['Ingresos ($)'] - tabla_resumen['Gastos ($)']
                
                total_entrado = df_fondo['Ingresos ($)'].sum()
                total_gastado = df_fondo['Gastos ($)'].sum()
                
                col_r1, col_r2, col_r3 = st.columns(3)
                col_r1.metric("Total Histórico Ingresado ($)", f"${total_entrado:.2f}")
                col_r2.metric("Total Histórico Gastado ($)", f"${total_gastado:.2f}")
                col_r3.metric("Saldo Actual Intacto ($)", f"${st.session_state.fondos[fondo_filtro]:.2f}")
                
                st.dataframe(tabla_resumen, use_container_width=True, hide_index=True)
                generar_botones_exportacion(tabla_resumen, f"Resumen del Fondo: {fondo_filtro}", "Resumen_Fondo", "tab4")
                
                with st.expander("Ver movimientos individuales"):
                    st.dataframe(df_fondo[["Fecha", "Tipo", "Concepto", "Monto ($)"]].sort_values(by="Fecha", ascending=False), use_container_width=True, hide_index=True)
            else:
                st.warning(f"El fondo '{fondo_filtro}' no tiene movimientos.")
        else:
            st.info("Aún no hay movimientos registrados.")

    # ---------------- TAB 5: COMPARACIÓN ING/EGR ----------------
    with tab5:
        st.write("### ⚖️ Comparativa: Ingresos Reales vs Egresos")
        st.write("Visualiza el rendimiento real del negocio. *(Nota: Las transferencias internas entre fondos no se cuentan, ya que no son ni gastos ni ingresos nuevos)*.")
        df_movs = preparar_dataframe_movimientos()
        if not df_movs.empty:
            df_movs['Fecha_DT'] = pd.to_datetime(df_movs['Fecha']).dt.date
            c_f1, c_f2 = st.columns(2)
            f_ini = c_f1.date_input("🗓️ Desde la fecha:", df_movs['Fecha_DT'].min())
            f_fin = c_f2.date_input("🗓️ Hasta la fecha:", datetime.today().date())
            mask = (df_movs['Fecha_DT'] >= f_ini) & (df_movs['Fecha_DT'] <= f_fin)
            df_filt = df_movs[mask]
            
            if not df_filt.empty:
                ing_reales = df_filt[df_filt["Tipo"] == "INGRESO"]["Monto ($)"].sum()
                egr_reales = abs(df_filt[df_filt["Tipo"].str.contains("EGRESO")]["Monto ($)"].sum())
                saldo_periodo = ing_reales - egr_reales
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Ingresos (Ventas) 📈", f"${ing_reales:.2f}")
                c2.metric("Egresos (Gastos + Nómina) 📉", f"${egr_reales:.2f}")
                c3.metric("Flujo de Caja Neto ⚖️", f"${saldo_periodo:.2f}", delta=f"{saldo_periodo:.2f}", delta_color="normal")
                
                st.write("#### 📊 Gráfico Comparativo")
                df_grafico = pd.DataFrame({
                    "Categoría": ["Ingresos Reales 📈", "Egresos Totales 📉"],
                    "Monto ($)": [ing_reales, egr_reales]
                }).set_index("Categoría")
                st.bar_chart(df_grafico, color=["#1e7e34"])
                
                datos_comparativa = [
                    {"Concepto": "Ingresos Reales (Por Cierres/Ventas)", "Total en el Rango ($)": round(ing_reales, 2)},
                    {"Concepto": "Egresos Totales (Gastos, Nóminas, Bonos)", "Total en el Rango ($)": round(egr_reales, 2)},
                    {"Concepto": "BALANCE NETO", "Total en el Rango ($)": round(saldo_periodo, 2)}
                ]
                generar_botones_exportacion(pd.DataFrame(datos_comparativa), f"Comparativa ING-EGR ({f_ini} al {f_fin})", "Comparativa", "tab5")
            else:
                st.warning("No hay registros en este rango de fechas.")
        else:
            st.info("Aún no hay movimientos registrados para comparar.")

    # ---------------- TAB 6: CAJA DE RESPALDO AVANZADA (MODO CAJA CHICA) ----------------
    with tab6:
        st.write("### 🏦 Bóveda de Respaldo (Caja Chica)")
        
        # --- BOTÓN MÁGICO DE RESETEO TEMPORAL ---
        if st.button("🚨 BORRAR SALDOS FANTASMA A CERO 🚨", type="primary"):
            st.session_state.respaldo_detalles["Dólares Físicos"] = 0.0
            st.session_state.respaldo_detalles["Bolívares Físicos"] = 0.0
            st.session_state.respaldo_detalles["Cuenta Bicentenario"] = 0.0
            guardar_json("respaldo_detalles.json", st.session_state.respaldo_detalles)
            actualizar_total_respaldo()
            guardar_json("fondos.json", st.session_state.fondos)
            st.rerun()
        # ----------------------------------------
        
        st.write("Inyecta capital base y fondos de emergencia por tipo de moneda.")
        
        # MOSTRAR SALDOS ESPECÍFICOS
        st.markdown("#### 📊 Saldos Actuales")
        col_res1, col_res2, col_res3 = st.columns(3)
        usd_fisico = st.session_state.respaldo_detalles["Dólares Físicos"]
        bs_fisico = st.session_state.respaldo_detalles["Bolívares Físicos"]
        banco_bicen = st.session_state.respaldo_detalles["Cuenta Bicentenario"]
        
        col_res1.markdown(f"<div class='metric-caja'><b>💵 Dólares Físicos</b><br><span style='font-size:24px; color:#28a745;'>${usd_fisico:.2f}</span></div>", unsafe_allow_html=True)
        col_res2.markdown(f"<div class='metric-caja'><b>💴 Bolívares Físicos</b><br><span style='font-size:24px; color:#17a2b8;'>{bs_fisico:.2f} BS</span></div>", unsafe_allow_html=True)
        col_res3.markdown(f"<div class='metric-caja'><b>🏦 Bicentenario</b><br><span style='font-size:24px; color:#007bff;'>{banco_bicen:.2f} BS</span></div>", unsafe_allow_html=True)
        
        st.write("")
        st.markdown("---")
        
        accion_respaldo = st.radio("¿Qué deseas registrar?", ["📥 Inyectar Capital", "💱 Cambio de Dólares"], horizontal=True)
        
        # 1. INYECTAR CAPITAL
        if accion_respaldo == "📥 Inyectar Capital":
            st.write("#### 📥 Registrar Inyección de Capital")
            with st.form("form_respaldo_avanzado"):
                cuenta_afectada = st.selectbox("¿En qué cuenta o moneda estás inyectando el dinero?", ["Dólares Físicos", "Bolívares Físicos", "Cuenta Bicentenario"])
                monto_operacion = st.number_input("Monto EXACTO a registrar", min_value=0.01, step=1.0)
                concepto_respaldo = st.text_input("Concepto / Motivo (Ej: Capital inicial, Préstamo, etc.)")
                
                if st.form_submit_button("📥 REGISTRAR INGRESO A LA BÓVEDA", use_container_width=True):
                    if not concepto_respaldo:
                        st.error("Debes ingresar un concepto.")
                    else:
                        monto_en_usd = monto_operacion if cuenta_afectada == "Dólares Físicos" else (monto_operacion / tasa)
                        fecha_op = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        st.session_state.respaldo_detalles[cuenta_afectada] += monto_operacion
                        registrar_movimiento("7. CAJA DE RESPALDO", "INGRESO", monto_en_usd, concepto_respaldo, fecha_exacta=fecha_op, monto_original=monto_operacion, moneda=cuenta_afectada)
                        
                        guardar_json("respaldo_detalles.json", st.session_state.respaldo_detalles)
                        actualizar_total_respaldo()
                        guardar_json("fondos.json", st.session_state.fondos)
                        st.success(f"¡Inyección de {monto_operacion} en {cuenta_afectada} registrada con éxito!")
                        st.rerun()

        # 2. CAMBIO DE DÓLARES
        else:
            st.write("#### 💱 Convertir Dólares a Bolívares")
            st.info(f"💡 Tasa de cálculo actual: **{tasa:.2f} BS/$**")
            with st.form("f_cambio_dolares"):
                usd_a_cambiar = st.number_input("Cantidad de Dólares Físicos que vas a vender/cambiar:", min_value=1.0, step=1.0)
                destino_cambio = st.selectbox("¿En qué cuenta van a caer los bolívares de ese cambio?", ["Bolívares Físicos", "Cuenta Bicentenario"])
                concepto_cambio = st.text_input("Concepto del cambio:", value="Cambio de divisas")
                
                total_bs_recibir = usd_a_cambiar * tasa
                st.warning(f"Se sumarán **{total_bs_recibir:.2f} BS** a tu {destino_cambio}.")
                
                if st.form_submit_button("💱 EJECUTAR CAMBIO", use_container_width=True):
                    if st.session_state.respaldo_detalles["Dólares Físicos"] >= usd_a_cambiar:
                        # 1. Restar dólares
                        st.session_state.respaldo_detalles["Dólares Físicos"] -= usd_a_cambiar
                        # 2. Sumar bolívares en el destino elegido
                        st.session_state.respaldo_detalles[destino_cambio] += total_bs_recibir
                        
                        fecha_op = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        # 3. Registrar Salida de USD
                        registrar_movimiento("7. CAJA DE RESPALDO", "RETIRO", -usd_a_cambiar, f"SALIDA POR CAMBIO: {concepto_cambio}", fecha_exacta=fecha_op, monto_original=-usd_a_cambiar, moneda="Dólares Físicos")
                        # 4. Registrar Entrada de BS
                        registrar_movimiento("7. CAJA DE RESPALDO", "INGRESO", usd_a_cambiar, f"ENTRADA POR CAMBIO: {concepto_cambio}", fecha_exacta=fecha_op, monto_original=total_bs_recibir, moneda=destino_cambio)
                        
                        guardar_json("respaldo_detalles.json", st.session_state.respaldo_detalles)
                        actualizar_total_respaldo()
                        guardar_json("fondos.json", st.session_state.fondos)
                        st.success("¡Cambio realizado! Saldos actualizados.")
                        st.rerun()
                    else:
                        st.error("No tienes suficientes Dólares Físicos en la Bóveda para hacer este cambio.")
                        
        st.markdown("---")
        st.write("#### 📜 Historial de Movimientos en la Caja de Respaldo")
        df_movs = preparar_dataframe_movimientos()
        if not df_movs.empty:
            df_respaldo = df_movs[df_movs['Fondo'] == "7. CAJA DE RESPALDO"].copy()
            if not df_respaldo.empty:
                df_respaldo = df_respaldo.sort_values(by="Fecha", ascending=False)
                
                st.dataframe(df_respaldo[["Fecha", "Tipo", "Concepto", "Monto Original", "Moneda"]], use_container_width=True, hide_index=True)
                generar_botones_exportacion(df_respaldo[["Fecha", "Tipo", "Concepto", "Monto Original", "Moneda"]], "Historial Caja de Respaldo", "Historial_Respaldo", "tab6")
                
                st.markdown("<div style='padding: 15px; border-radius: 8px; border: 1px solid #f5c6cb; background-color: #f8d7da; margin-top: 15px;'>", unsafe_allow_html=True)
                st.write("##### 🗑️ Eliminar Movimiento Permanentemente")
                st.write("Al eliminar una operación, se borrará para siempre del historial y su monto se reversará automáticamente de los **Saldos Actuales** de arriba.")
                
                # Se ocultan las transferencias para que se borren en Tab 3 y no haya cruces matemáticos, pero se muestran Inyecciones y Cambios
                opciones_r = [f"{row['Fecha']} | {row['Concepto']} | {row['Monto Original']:.2f} {row['Moneda']}" for idx, row in df_respaldo.iterrows() if "TRANSF." not in row['Tipo']]
                
                r_a_borrar = st.selectbox("Seleccione la operación a eliminar:", opciones_r)
                
                if st.button("🗑️ ELIMINAR OPERACIÓN", type="primary"):
                    if r_a_borrar:
                        fecha_borrar = r_a_borrar.split(" | ")[0]
                        deshacer_operacion(fecha_borrar)
                        st.success("¡Operación eliminada para siempre y Saldos Actuales actualizados!")
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("Aún no hay movimientos en la Caja de Respaldo.")
        else:
            st.info("Aún no hay movimientos registrados.")

    st.write("")
    st.markdown("---")
    if st.button("⬅ VOLVER AL MENÚ PRINCIPAL", use_container_width=True):
        st.session_state.menu_principal = "Escritorio" 
        st.rerun()

def ejecutar():
    inicializar_estado()
    aplicar_css()
    mostrar_ingresos_egresos()

if __name__ == "__main__":
    ejecutar()