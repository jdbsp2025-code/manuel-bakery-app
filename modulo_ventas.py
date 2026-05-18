import streamlit as st
import pandas as pd
from datetime import datetime
import tempfile
import base64
from utilidades import cargar_json, guardar_json 

try:
    from fpdf import FPDF
    FPDF_DISPONIBLE = True
except ImportError:
    FPDF_DISPONIBLE = False

# ==========================================
# 1. CONFIGURACIÓN INICIAL
# ==========================================
ORDEN_CATEGORIAS = ["PAN SALADO", "PAN DULCE", "REPOSTERIA", "HELADOS", "VIVERES"]

def inicializar_estado():
    if 'carrito' not in st.session_state: st.session_state.carrito = [] 
    if 'vista' not in st.session_state: st.session_state.vista = "POS" 
    
    if 'facturas' not in st.session_state: st.session_state.facturas = cargar_json("facturas.json", []) 
    if 'db_vitrina' not in st.session_state: st.session_state.db_vitrina = cargar_json("vitrina.json", [])
    if 'cuentas_por_cobrar' not in st.session_state: st.session_state.cuentas_por_cobrar = cargar_json("cuentas_cobrar.json", [])
    if 'historial_pagos_fiao' not in st.session_state: st.session_state.historial_pagos_fiao = cargar_json("pagos_fiao.json", [])
        
    if 'tasa_bcv' not in st.session_state: st.session_state.tasa_bcv = 36.50
    if 'turno_actual' not in st.session_state: st.session_state.turno_actual = "TURNO NO ASIGNADO"

    if 'fondos' not in st.session_state: st.session_state.fondos = cargar_json("fondos.json", {})
    if 'db_movimientos_fondos' not in st.session_state: st.session_state.db_movimientos_fondos = cargar_json("movimientos_fondos.json", [])
    
    claves_necesarias = [
        "1. Materia Prima (Reposición)", "2. Productores (Nómina 60%)", 
        "3. Gastos Operativos (Transp/Internet 20%)", "4. Mantenimiento y Papelería (10%)",
        "5. Utilidad Libre (Dueño/Compartir 10%)", "6. Subfondo Inasistencias (Bonos)", "7. CAJA DE RESPALDO"
    ]
    for clave in claves_necesarias:
        if clave not in st.session_state.fondos:
            st.session_state.fondos[clave] = 0.0

# ==========================================
# 2. LÓGICA DE VENTAS
# ==========================================
def procesar_venta(metodo, desglose, total, cliente=None):
    fecha_manual = st.session_state.get('fecha_venta_manual', datetime.today())
    fecha_str = f"{fecha_manual.strftime('%d/%m/%Y')} {datetime.now().strftime('%H:%M')}"
    
    detalle_items = ", ".join([f"{i['Cant']}x {i['Producto']}" for i in st.session_state.carrito])
    
    st.session_state.facturas.append({
        "fecha": fecha_str,
        "metodo": metodo,
        "total": total,
        "desglose": desglose,
        "items": st.session_state.carrito.copy(),
        "cliente": cliente,
        "detalle_texto": detalle_items
    })
    
    if metodo == "CRÉDITO (FIAO)":
        tasa = st.session_state.get('tasa_bcv', 36.50)
        deuda_usd = round(total / tasa, 2)
        
        cliente_existe = False
        for c in st.session_state.cuentas_por_cobrar:
            if c["cliente"].lower() == cliente.lower() and c["estado"] == "Pendiente":
                c["monto_usd"] += deuda_usd
                c["monto_bs_historico"] += total
                c["detalle"] = c.get("detalle", "") + " | " + detalle_items
                cliente_existe = True
                break
                
        if not cliente_existe:
            st.session_state.cuentas_por_cobrar.append({
                "cliente": cliente,
                "fecha_inicio": fecha_manual.strftime('%d/%m/%Y'),
                "monto_usd": deuda_usd,
                "monto_bs_historico": total, 
                "detalle": detalle_items,
                "estado": "Pendiente"
            })
        guardar_json("cuentas_cobrar.json", st.session_state.cuentas_por_cobrar)
    
    for item_vendido in st.session_state.carrito:
        for prod_inv in st.session_state.db_vitrina:
            if prod_inv["Producto"] == item_vendido["Producto"]:
                prod_inv["Stock"] -= item_vendido["Cant"]
                break
                
    guardar_json("facturas.json", st.session_state.facturas)
    guardar_json("vitrina.json", st.session_state.db_vitrina)
    st.session_state.carrito.clear() 
    st.success(f"¡Venta {metodo} registrada!")
    st.rerun()

def inyectar_pago_deuda(cliente, monto_v, metodo_v, concepto, nombre_prod, costo_prod, precio_prod):
    tasa = st.session_state.tasa_bcv
    desglose = {"bs_efectivo": 0.0, "bs_pagomovil": 0.0, "bs_punto": 0.0, "usd_efectivo": 0.0, "usd_en_bs": 0.0}
    
    if metodo_v == "PUNTO DE VENTA": desglose["bs_punto"] = monto_v
    elif metodo_v == "PAGO MÓVIL": desglose["bs_pagomovil"] = monto_v
    elif metodo_v == "EFECTIVO": desglose["bs_efectivo"] = monto_v
    elif metodo_v == "DÓLARES": 
        desglose["usd_efectivo"] = monto_v
        desglose["usd_en_bs"] = monto_v * tasa
        monto_v = monto_v * tasa 
    
    detalle_final = concepto
    if nombre_prod:
        detalle_final += f" | Prod: {nombre_prod}"
        if costo_prod: detalle_final += f" | Costo Ref: {costo_prod}"
        if precio_prod: detalle_final += f" | Precio Ref: {precio_prod}"
        
    fecha_str = f"{datetime.today().strftime('%d/%m/%Y')} {datetime.now().strftime('%H:%M')}"
    
    st.session_state.facturas.append({
        "fecha": fecha_str,
        "metodo": f"PAGO DE DEUDA ({metodo_v})",
        "total": monto_v,
        "desglose": desglose,
        "items": [], 
        "cliente": cliente,
        "detalle_texto": detalle_final
    })
    guardar_json("facturas.json", st.session_state.facturas)

# ==========================================
# 3. GENERADOR DE PDF (CON CATEGORÍAS CHECK-LIST)
# ==========================================
def generar_pdf_cierre(totales, df_vitrina, cuentas_por_cobrar, facturas_turno, fecha_cierre_str):
    if not FPDF_DISPONIBLE: return None
        
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="CIERRE DE CAJA - COMUNAPP", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Fecha: {fecha_cierre_str} | Turno: {st.session_state.get('turno_actual', 'N/A')}", ln=True)
    pdf.ln(5)
    
    # SECCIÓN 1: FINANZAS
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="1. RESUMEN FINANCIERO DEL TURNO", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 8, txt=f"Efectivo Fisico: {totales['efectivo']:.2f} BS", ln=True)
    pdf.cell(200, 8, txt=f"Punto de Venta: {totales['punto']:.2f} BS", ln=True)
    pdf.cell(200, 8, txt=f"Pago Movil: {totales['pm']:.2f} BS", ln=True)
    pdf.cell(200, 8, txt=f"Dolar Fisico: {totales['usd']:.2f} $", ln=True)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 8, txt=f"TOTAL INGRESADO EN CAJA: {totales['real']:.2f} BS", ln=True)
    pdf.set_text_color(220, 53, 69)
    pdf.cell(200, 8, txt=f"Mercancia Fiada (Creditos del turno): {totales['fiao']:.2f} BS", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    
    # SECCIÓN 2: PAGOS DE DEUDAS INYECTADOS
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="2. CUENTAS PAGADAS EN ESTE TURNO", ln=True)
    pagos_deuda = [f for f in facturas_turno if "PAGO DE DEUDA" in f["metodo"]]
    
    if pagos_deuda:
        for p in pagos_deuda:
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(100, 6, txt=f"Cliente: {str(p['cliente']).upper()}", border=0)
            pdf.cell(50, 6, txt=f"Pago: {p['total']:.2f} BS", border=0, ln=True)
            pdf.set_font("Arial", 'I', 9)
            pdf.multi_cell(0, 6, txt=f"Metodo: {p['metodo']} | Ref: {p.get('detalle_texto', '')}", border=0)
            pdf.line(10, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(2)
    else:
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 10, txt="No se registraron cobros de deudas (Fiaos) en este turno.", ln=True)
        
    pdf.ln(5)
    
    # SECCIÓN 3: VITRINA POR CATEGORÍAS (CHECK-LIST)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="3. INVENTARIO RESTANTE (VITRINA)", ln=True)
    
    if not df_vitrina.empty:
        categorias = df_vitrina['Categoría'].unique()
        for cat in categorias:
            pdf.set_font("Arial", 'B', 11)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(175, 8, txt=f" [ {cat} ]", border=1, ln=True, fill=True)
            
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(50, 8, txt="Producto", border=1)
            pdf.cell(25, 8, txt="Inicial", border=1, align='C')
            pdf.cell(25, 8, txt="Entrada", border=1, align='C')
            pdf.cell(25, 8, txt="Vendida", border=1, align='C')
            pdf.cell(25, 8, txt="Fiada", border=1, align='C')
            pdf.cell(25, 8, txt="Restante", border=1, align='C', ln=True)
            
            pdf.set_font("Arial", size=8)
            df_cat = df_vitrina[df_vitrina['Categoría'] == cat]
            for _, row in df_cat.iterrows():
                pdf.cell(50, 8, txt=str(row['Producto'])[:22], border=1)
                pdf.cell(25, 8, txt=str(row['Inicial']), border=1, align='C')
                pdf.cell(25, 8, txt=str(row['Entrada']), border=1, align='C')
                pdf.cell(25, 8, txt=str(row['Vendida']), border=1, align='C')
                pdf.cell(25, 8, txt=str(row['Fiada']), border=1, align='C')
                pdf.cell(25, 8, txt=str(row['Restante']), border=1, align='C', ln=True)
            pdf.ln(3)
    else:
        pdf.set_font("Arial", size=10)
        pdf.cell(180, 10, txt="No se registraron movimientos en vitrina.", border=1, align='C', ln=True)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()

# ==========================================
# 4. VENTANAS EMERGENTES (POP-UPS DE PAGO FLEXIBLE)
# ==========================================
@st.dialog("📝 Registrar Venta a Crédito (FIAO)")
def dialogo_credito():
    total = sum(item['Total'] for item in st.session_state.carrito)
    tasa = st.session_state.tasa_bcv
    st.markdown(f"<h3 style='color:#dc3545;'>Total a Fiar: {total:.2f} BS (${total/tasa:.2f})</h3>", unsafe_allow_html=True)
    nombre_cliente = st.text_input("Nombre de la persona que se lleva el producto:")
    
    col1, col2 = st.columns(2)
    if col1.button("✅ CONFIRMAR FIAO", type="primary", use_container_width=True):
        if nombre_cliente.strip():
            desglose = {"bs_efectivo": 0.0, "bs_pagomovil": 0.0, "bs_punto": 0.0, "usd_efectivo": 0.0, "usd_en_bs": 0.0}
            procesar_venta("CRÉDITO (FIAO)", desglose, total, cliente=nombre_cliente.strip().upper())
        else:
            st.error("⚠️ Debes ingresar el nombre del cliente.")
    if col2.button("❌ CANCELAR", use_container_width=True): st.rerun()

@st.dialog("🏦 Pago usando Fondos Internos")
def dialogo_pago_fondos():
    total = sum(item['Total'] for item in st.session_state.carrito)
    tasa = st.session_state.tasa_bcv
    total_usd = total / tasa
    
    st.write("Usa esta opción si un empleado o dueño saca un pan y se pagará con el dinero de los fondos de la panadería (No suma al corte de caja de hoy).")
    st.markdown(f"<h2 style='color:#2196F3;'>Costo de los panes: {total:.2f} BS (${total_usd:.2f} USD)</h2>", unsafe_allow_html=True)
    
    fondos_operativos = [k for k in st.session_state.fondos.keys() if k != "7. CAJA DE RESPALDO"]
    fondo_sel = st.selectbox("¿De qué Fondo se descontará el dinero?", fondos_operativos)
    
    saldo_disp_usd = st.session_state.fondos.get(fondo_sel, 0.0)
    saldo_disp_bs = saldo_disp_usd * tasa
    st.info(f"💰 Saldo disponible en {fondo_sel}: **${saldo_disp_usd:.2f} USD** (Eq: {saldo_disp_bs:.2f} BS)")
    
    concepto = st.text_input("Concepto / Motivo de la salida:", placeholder="Ej: Merienda empleados, consumo interno...")
    
    col1, col2 = st.columns(2)
    if col1.button("✅ CONFIRMAR Y DESCONTAR", type="primary", use_container_width=True):
        if not concepto.strip():
            st.error("⚠️ Debes escribir un concepto.")
        elif total_usd > saldo_disp_usd:
            st.error("❌ Fondos insuficientes. No hay suficiente dinero en esa cuenta para pagar estos panes.")
        else:
            st.session_state.fondos[fondo_sel] -= total_usd
            guardar_json("fondos.json", st.session_state.fondos)
            
            st.session_state.db_movimientos_fondos.append({
                "Fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "Fondo": fondo_sel, "Tipo": "EGRESO", "Monto ($)": -total_usd,
                "Monto Original": -total, "Moneda": "BS", "Concepto": f"Autopago de Venta en Caja: {concepto}"
            })
            guardar_json("movimientos_fondos.json", st.session_state.db_movimientos_fondos)
            
            desglose = {"bs_efectivo": 0.0, "bs_pagomovil": 0.0, "bs_punto": 0.0, "usd_efectivo": 0.0, "usd_en_bs": 0.0}
            procesar_venta("PAGO CON FONDOS", desglose, total, cliente=f"Fondo: {fondo_sel}")
            
    if col2.button("❌ CANCELAR", use_container_width=True): st.rerun()

@st.dialog("Confirmación de Pago Rápido")
def dialogo_pago_rapido(metodo):
    total = sum(item['Total'] for item in st.session_state.carrito)
    tasa = st.session_state.tasa_bcv
    st.write(f"### Método: {metodo}")
    st.dataframe(pd.DataFrame(st.session_state.carrito), hide_index=True)
    st.markdown(f"<h2 style='color:#68A042;'>Costo de los panes: {total:.2f} BS</h2>", unsafe_allow_html=True)
    
    desglose = {"bs_efectivo": 0.0, "bs_pagomovil": 0.0, "bs_punto": 0.0, "usd_efectivo": 0.0, "usd_en_bs": 0.0}
    aceptar = True

    if metodo == "DÓLARES":
        st.markdown(f"<h3 style='color:#2196F3;'>Equivalente en Dólares: ${total/tasa:.2f}</h3>", unsafe_allow_html=True)
        monto_pagado_usd = st.number_input("Monto del billete recibido en DÓLARES ($):", min_value=0.0, value=float(round(total/tasa, 2)), step=1.0)
        
        ingresado_bs = round(monto_pagado_usd * tasa, 2)
        diferencia = round(ingresado_bs - total, 2)
        
        dar_vuelto = True
        if diferencia < 0:
            st.warning(f"⚠️ El billete no alcanza. Faltan {abs(diferencia):.2f} BS para cubrir el costo exacto.")
            aceptar = st.checkbox("☑️ Aceptar pago incompleto (Se le vende así con descuento/faltante)")
        elif diferencia > 0:
            st.success(f"💡 Cambio a devolver al cliente: {diferencia:.2f} BS")
            dar_vuelto = st.checkbox("☑️ Se le entregó el vuelto exacto al cliente en Bolívares", value=True)
            if not dar_vuelto:
                st.info("El dinero extra quedará registrado como sobrante/propina a favor de la caja.")
        
        col1, col2 = st.columns(2)
        if col1.button("✅ CONFIRMAR Y FACTURAR", use_container_width=True, disabled=not aceptar):
            desglose["usd_efectivo"] = monto_pagado_usd
            desglose["usd_en_bs"] = ingresado_bs
            
            if diferencia > 0 and dar_vuelto:
                desglose["bs_efectivo"] = -diferencia 
                
            procesar_venta(metodo, desglose, total)
        if col2.button("❌ CANCELAR", use_container_width=True): st.rerun()

    else:
        monto_pagado = st.number_input(f"Monto REALMENTE recibido en {metodo} (BS):", min_value=0.0, value=float(total), step=1.0)
        diferencia = round(monto_pagado - total, 2)
        
        dar_vuelto = True
        if diferencia < 0:
            st.warning(f"⚠️ Faltan {abs(diferencia):.2f} BS para cubrir el costo exacto.")
            aceptar = st.checkbox("☑️ Aceptar pago incompleto (Se le vende así con descuento/faltante)")
        elif diferencia > 0:
            st.success(f"💡 Cambio a devolver: {diferencia:.2f} BS")
            dar_vuelto = st.checkbox("☑️ Se le entregó el vuelto exacto al cliente", value=True)
            if not dar_vuelto:
                st.info("El dinero extra quedará registrado como sobrante/propina en la caja.")
        
        col1, col2 = st.columns(2)
        if col1.button("✅ CONFIRMAR Y FACTURAR", use_container_width=True, disabled=not aceptar):
            ingreso_real = total if (diferencia > 0 and dar_vuelto) else monto_pagado
            
            if metodo == "EFECTIVO": desglose["bs_efectivo"] = ingreso_real
            elif metodo == "PAGO MÓVIL": desglose["bs_pagomovil"] = ingreso_real
            elif metodo == "PUNTO DE VENTA": desglose["bs_punto"] = ingreso_real
            
            procesar_venta(metodo, desglose, total)
        if col2.button("❌ CANCELAR", use_container_width=True): st.rerun()

@st.dialog("Pago Múltiple (Mixto)")
def dialogo_multipago():
    total = sum(item['Total'] for item in st.session_state.carrito)
    tasa = st.session_state.tasa_bcv
    st.write(f"**A Cobrar:** {total:.2f} BS")
    
    b_ef = st.number_input("Bolívares Efectivo", 0.0)
    b_pm = st.number_input("Pago Móvil", 0.0)
    b_pt = st.number_input("Punto", 0.0)
    u_ef = st.number_input("Dólares ($)", 0.0)
    
    tot_ing = b_ef + b_pm + b_pt + (u_ef * tasa)
    rest = total - tot_ing
    
    if rest > 0: st.warning(f"Faltan {rest:.2f} BS")
    else: st.success(f"Vuelto: {abs(rest):.2f} BS")
    
    if st.button("✅ PROCESAR PAGO", disabled=(rest > 0)):
        desglose = {"bs_efectivo": b_ef + rest if rest < 0 else b_ef, "bs_pagomovil": b_pm, "bs_punto": b_pt, "usd_efectivo": u_ef, "usd_en_bs": u_ef*tasa}
        procesar_venta("MULTIPAGO (MIXTO)", desglose, total)

@st.dialog("Resumen de Cierre de Caja", width="large")
def dialogo_cierre():
    fecha_cierre = st.date_input("📅 Fecha para este Cierre (Ajustar si es de ayer)", st.session_state.get('fecha_venta_manual', datetime.today()))
    fecha_cierre_str = f"{fecha_cierre.strftime('%d/%m/%Y')} {datetime.now().strftime('%H:%M')}"
    fecha_cierre_solo_dia = fecha_cierre.strftime('%Y-%m-%d')
    
    st.write("### 💰 Ingresos Físicos Reales en Caja")
    
    tasa_cierre = st.session_state.get('tasa_bcv', 36.50)
    
    tot_ef = sum(f['desglose']['bs_efectivo'] for f in st.session_state.facturas)
    tot_pt = sum(f['desglose']['bs_punto'] for f in st.session_state.facturas)
    tot_pm = sum(f['desglose']['bs_pagomovil'] for f in st.session_state.facturas)
    tot_usd = sum(f['desglose']['usd_efectivo'] for f in st.session_state.facturas)
    tot_fiao = sum(f['total'] for f in st.session_state.facturas if f['metodo'] == "CRÉDITO (FIAO)")
    
    real_ingresado = tot_ef + tot_pt + tot_pm + (tot_usd * tasa_cierre)
    
    totales = {"efectivo": tot_ef, "punto": tot_pt, "pm": tot_pm, "usd": tot_usd, "fiao": tot_fiao, "real": real_ingresado}
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Efectivo (BS)", f"{totales['efectivo']:.2f}")
    col2.metric("Punto (BS)", f"{totales['punto']:.2f}")
    col3.metric("P. Móvil (BS)", f"{totales['pm']:.2f}")
    col4.metric("Dólares ($)", f"{totales['usd']:.2f}")
    
    st.markdown(f"<h3 style='color:#68A042;'>TOTAL INGRESADO EN CAJA: {totales['real']:.2f} BS</h3>", unsafe_allow_html=True)
    st.markdown(f"<h5 style='color:#dc3545;'>Deudas Nuevas (Fiado): {totales['fiao']:.2f} BS</h5>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.write("### 📦 Inventario Restante en Vitrina (Cantidades)")
    
    cats_disponibles = sorted(list(set([p.get("Categoría", "Otros") for p in st.session_state.db_vitrina])))
    cats_ordenadas = [c for c in ORDEN_CATEGORIAS if c in cats_disponibles] + [c for c in cats_disponibles if c not in ORDEN_CATEGORIAS]
    
    seleccion_cat = st.multiselect("Marque las categorías que desea incluir en el reporte:", cats_ordenadas, default=cats_ordenadas)
    
    resumen_vitrina = []
    productos_del_turno_para_historial = {}
    
    for p in st.session_state.db_vitrina:
        cat = p.get("Categoría", "Otros")
        if cat not in seleccion_cat: 
            continue
            
        nombre = p["Producto"]
        cant_vendida = 0
        cant_fiada = 0
        entradas_turno = p.get("Entradas_Turno", 0)
        
        for f in st.session_state.facturas:
            es_fiao = (f['metodo'] == "CRÉDITO (FIAO)")
            for item in f['items']: 
                if item['Producto'] == nombre:
                    if es_fiao: cant_fiada += item['Cant']
                    else: cant_vendida += item['Cant']
                    
                    if nombre in productos_del_turno_para_historial:
                        productos_del_turno_para_historial[nombre] += item['Cant']
                    else:
                        productos_del_turno_para_historial[nombre] = item['Cant']

        stock_restante = p["Stock"]
        vitrina_inicial = stock_restante + cant_vendida + cant_fiada - entradas_turno
        if vitrina_inicial < 0: vitrina_inicial = 0
        
        if cant_vendida > 0 or cant_fiada > 0 or entradas_turno > 0 or stock_restante > 0 or vitrina_inicial > 0:
            resumen_vitrina.append({
                "Categoría": cat,
                "Producto": nombre, 
                "Inicial": vitrina_inicial, 
                "Entrada": entradas_turno,
                "Vendida": cant_vendida, 
                "Fiada": cant_fiada, 
                "Restante": stock_restante
            })
        
    df_vitrina = pd.DataFrame(resumen_vitrina)
    if not df_vitrina.empty:
        df_vitrina['Cat_Index'] = df_vitrina['Categoría'].apply(lambda x: ORDEN_CATEGORIAS.index(x) if x in ORDEN_CATEGORIAS else 99)
        df_vitrina = df_vitrina.sort_values(by=['Cat_Index', 'Producto']).drop(columns=['Cat_Index'])
        st.dataframe(df_vitrina, hide_index=True, use_container_width=True)
    else:
        st.info("ℹ️ No se registraron ventas ni fiados de ningún producto durante este turno.")
        
    lista_productos_final = [{"Producto": k, "Cant": v} for k, v in productos_del_turno_para_historial.items()]

    st.error("⚠️ Al presionar guardar, la caja del turno quedará en 0.00 BS, pero mantendrás tu turno activo.")
    
    col_pdf, col_cerrar = st.columns([1, 2])
    with col_pdf:
        if FPDF_DISPONIBLE:
            pdf_bytes = generar_pdf_cierre(totales, df_vitrina, st.session_state.cuentas_por_cobrar, st.session_state.facturas, fecha_cierre_str)
            st.download_button(label="📄 Descargar PDF AHORA", data=pdf_bytes, file_name=f"Cierre_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)
        else:
            st.warning("Instalar FPDF (pip install fpdf)")
            
    with col_cerrar:
        if st.button("📤 GUARDAR CIERRE Y LIMPIAR CAJA", type="primary", use_container_width=True):
            if 'historial_cierres' not in st.session_state: 
                st.session_state.historial_cierres = cargar_json("historial_cierres.json", [])
            
            pdf_para_guardar = generar_pdf_cierre(totales, df_vitrina, st.session_state.cuentas_por_cobrar, st.session_state.facturas, fecha_cierre_str) if FPDF_DISPONIBLE else None
            pdf_b64 = base64.b64encode(pdf_para_guardar).decode('utf-8') if pdf_para_guardar else None

            st.session_state.historial_cierres.append({
                "fecha_hora": fecha_cierre_str,
                "fecha": fecha_cierre_solo_dia,
                "turno": st.session_state.get('turno_actual', 'TURNO NO ASIGNADO'),
                "total_bs": totales['real'],
                "fiao_bs": totales['fiao'],
                "efectivo_bs": totales['efectivo'],
                "punto_bs": totales['punto'],
                "pm_bs": totales['pm'],
                "usd_fisico": totales['usd'],
                "productos": lista_productos_final,
                "pdf_bytes_b64": pdf_b64,
                "facturas_respaldo": st.session_state.facturas.copy() 
            })
            
            guardar_json("historial_cierres.json", st.session_state.historial_cierres)
            st.session_state.facturas.clear()
            guardar_json("facturas.json", st.session_state.facturas)
            for p in st.session_state.db_vitrina: p["Entradas_Turno"] = 0
            guardar_json("vitrina.json", st.session_state.db_vitrina)
            
            st.session_state.carrito.clear()
            st.session_state.vista = "POS" 
            st.success("¡Turno guardado exitosamente!")
            st.rerun()

# ==========================================
# 5. MÓDULO DE CUENTAS POR COBRAR
# ==========================================
def mostrar_cuentas_cobrar():
    st.markdown("<h1 style='text-align: center; color: #D35400;'>📓 CUENTAS POR COBRAR (FIAO)</h1>", unsafe_allow_html=True)
    if st.button("⬅ VOLVER A REPORTES", use_container_width=True):
        st.session_state.vista = "REPORTES"; st.rerun()
        
    tab1, tab2, tab3 = st.tabs(["🔴 Deudas Activas", "💵 Pago de Deuda Registrada", "⚠️ Cobrar Fiao Viejo / Externo"])
    
    with tab1:
        st.write("### Clientes con saldo pendiente")
        deudas_activas = [c for c in st.session_state.cuentas_por_cobrar if c["estado"] == "Pendiente"]
        if deudas_activas:
            for d in deudas_activas:
                if "detalle" not in d: d["detalle"] = "Sin detalle"
                
            df_deudas = pd.DataFrame(deudas_activas)[["cliente", "fecha_inicio", "monto_usd", "detalle", "estado"]]
            df_deudas.rename(columns={"cliente":"Cliente", "fecha_inicio": "Fecha", "monto_usd": "Deuda Act. (USD $)"}, inplace=True)
            st.dataframe(df_deudas, use_container_width=True, hide_index=True)
        else: st.success("¡Nadie debe!")
        
        st.markdown("---")
        st.markdown("##### 🗑️ Eliminar Deuda Activa")
        cliente_a_borrar = st.selectbox("Seleccione el cliente cuya deuda desea eliminar:", [""] + [c["cliente"] for c in deudas_activas])
        if st.button("❌ Eliminar Deuda Permanentemente", type="primary"):
            if cliente_a_borrar:
                st.session_state.cuentas_por_cobrar = [c for c in st.session_state.cuentas_por_cobrar if not (c["cliente"] == cliente_a_borrar and c["estado"] == "Pendiente")]
                guardar_json("cuentas_cobrar.json", st.session_state.cuentas_por_cobrar)
                st.success(f"Deuda de {cliente_a_borrar} eliminada.")
                st.rerun()
        
    with tab2:
        st.write("### 💵 Ingresar pago de deuda a la caja de hoy")
        if deudas_activas:
            cliente = st.selectbox("Seleccione Cliente:", [c["cliente"] for c in deudas_activas])
            datos = next(c for c in st.session_state.cuentas_por_cobrar if c["cliente"] == cliente and c["estado"] == "Pendiente")
            tasa = st.session_state.tasa_bcv
            st.warning(f"Deuda de {cliente}: ${datos['monto_usd']:.2f} ({datos['monto_usd']*tasa:.2f} BS)\n\nLlevó: {datos.get('detalle', 'N/A')}")
            
            with st.form("form_pago_registrada"):
                metodo_pago = st.selectbox("¿Cómo está pagando el cliente?", ["PUNTO DE VENTA", "PAGO MÓVIL", "EFECTIVO", "DÓLARES"])
                monto = st.number_input("Monto que está pagando:", min_value=1.0)
                
                st.write("**Detalle Opcional del Producto Cobrado (No descuenta de vitrina):**")
                c1, c2, c3 = st.columns(3)
                nombre_prod = c1.text_input("Nombre del Producto:")
                costo_prod = c2.text_input("Costo Ref:")
                precio_prod = c3.text_input("Precio Ref:")
                concepto = st.text_input("Concepto / Notas del pago:", value="Abono a deuda")
                
                if st.form_submit_button("✅ REGISTRAR PAGO A LA CAJA", use_container_width=True):
                    abono_usd = round(monto / tasa, 2) if metodo_pago != "DÓLARES" else monto
                    monto_bs_historico = monto if metodo_pago != "DÓLARES" else (monto * tasa)
                    
                    datos["monto_usd"] -= abono_usd
                    if datos["monto_usd"] <= 0.05: datos["monto_usd"] = 0; datos["estado"] = "Pagado"
                    st.session_state.historial_pagos_fiao.append({"Fecha": datetime.now().strftime('%d/%m/%Y'), "Cliente": cliente, "Abono BS": monto_bs_historico, "Abono USD $": abono_usd, "Tasa": tasa})
                    
                    inyectar_pago_deuda(cliente, monto, metodo_pago, concepto, nombre_prod, costo_prod, precio_prod)
                    
                    guardar_json("cuentas_cobrar.json", st.session_state.cuentas_por_cobrar)
                    guardar_json("pagos_fiao.json", st.session_state.historial_pagos_fiao)
                    st.success("¡Pago registrado! El dinero se sumó a las facturas del turno actual.")
                    st.rerun()
        else: st.info("No hay deudas.")
                
    with tab3:
        st.write("### 🚨 Cobrar Deuda Vieja (No registrada en sistema)")
        st.info("El dinero de este fiao viejo ingresará al cierre de caja actual para cuadrar Punto/Efectivo, sin descontar panes de la vitrina.")
        
        with st.form("fiao_viejo"):
            cli_viejo = st.text_input("Nombre del Cliente (Fiao Viejo):")
            metodo_v = st.selectbox("¿Cómo te pagó?", ["PUNTO DE VENTA", "PAGO MÓVIL", "EFECTIVO", "DÓLARES"])
            monto_v = st.number_input("Monto pagado:", min_value=1.0)
            
            st.write("**Detalle Opcional del Producto Cobrado (No descuenta de vitrina):**")
            c1, c2, c3 = st.columns(3)
            nombre_prod = c1.text_input("Nombre del Producto:")
            costo_prod = c2.text_input("Costo Ref:")
            precio_prod = c3.text_input("Precio Ref:")
            concepto = st.text_input("Concepto / Notas del pago:", value="Pago de Fiao Viejo")
            
            if st.form_submit_button("✅ INGRESAR DINERO A LA CAJA ACTUAL", use_container_width=True):
                if cli_viejo:
                    inyectar_pago_deuda(cli_viejo, monto_v, metodo_v, concepto, nombre_prod, costo_prod, precio_prod)
                    st.success("¡Dinero del fiao viejo ingresado a la caja del turno actual!")
                    st.rerun()
                else: st.error("Falta el nombre del cliente.")

# ==========================================
# 6. VISTA DE REPORTES PRINCIPAL
# ==========================================
def mostrar_reportes():
    st.markdown("""<style>button:has(div p:contains("VOLVER AL MENÚ PRINCIPAL")) {background-color: #dc3545 !important; color: white !important; border: 2px solid #dc3545 !important;}button:has(div p:contains("VOLVER AL MENÚ PRINCIPAL")):hover {background-color: #c82333 !important; border: 2px solid #c82333 !important;}</style>""", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #68A042;'>📊 REPORTES DE VENTA DEL TURNO</h1>", unsafe_allow_html=True)
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("⬅ VOLVER A VENTAS (CAJA)", use_container_width=True): st.session_state.vista = "POS"; st.rerun()
    with col_btn2:
        if st.button("📓 CUENTAS POR COBRAR", use_container_width=True): st.session_state.vista = "CUENTAS_COBRAR"; st.rerun()
    with col_btn3:
        if st.button("🔒 REALIZAR CIERRE DE TURNO", type="primary", use_container_width=True): dialogo_cierre()
    st.markdown("---")
    
    total_ef = sum(f['desglose']['bs_efectivo'] for f in st.session_state.facturas)
    total_pt = sum(f['desglose']['bs_punto'] for f in st.session_state.facturas)
    total_pm = sum(f['desglose']['bs_pagomovil'] for f in st.session_state.facturas)
    total_usd = sum(f['desglose']['usd_efectivo'] for f in st.session_state.facturas)
    
    st.markdown(f"""
        <div style="display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 20px;">
            <div style="flex: 1; background-color: #4CAF50; padding: 20px; border-radius: 10px; color: white; text-align: center;">
                <h4 style="margin:0;">💵 EFECTIVO (BS)</h4><h2 style="margin:10px 0 0 0;">{total_ef:.2f} BS</h2></div>
            <div style="flex: 1; background-color: #2196F3; padding: 20px; border-radius: 10px; color: white; text-align: center;">
                <h4 style="margin:0;">💳 PUNTO DE VENTA</h4><h2 style="margin:10px 0 0 0;">{total_pt:.2f} BS</h2></div>
            <div style="flex: 1; background-color: #9C27B0; padding: 20px; border-radius: 10px; color: white; text-align: center;">
                <h4 style="margin:0;">📱 PAGO MÓVIL</h4><h2 style="margin:10px 0 0 0;">{total_pm:.2f} BS</h2></div>
            <div style="flex: 1; background-color: #E67E22; padding: 20px; border-radius: 10px; color: white; text-align: center;">
                <h4 style="margin:0;">💵 DÓLARES ($)</h4><h2 style="margin:10px 0 0 0;">{total_usd:.2f} $</h2></div>
        </div>
    """, unsafe_allow_html=True)
    
    st.write("### 🧾 Consolidado de Facturas y Pagos del Turno")
    if not st.session_state.facturas: 
        st.info("Aún no hay ventas registradas ni pagos cobrados.")
    else:
        datos_tabla = []
        for f in st.session_state.facturas:
            d = f['desglose']
            pagos = []
            if d['bs_efectivo'] > 0: pagos.append(f"Efec: {d['bs_efectivo']} BS")
            if d['bs_punto'] > 0: pagos.append(f"Pto: {d['bs_punto']} BS")
            if d['bs_pagomovil'] > 0: pagos.append(f"PM: {d['bs_pagomovil']} BS")
            if d['usd_efectivo'] > 0: pagos.append(f"USD: ${d['usd_efectivo']}")
            
            tipo_mov = f['metodo']
            if "DEUDA" in tipo_mov: tipo_mov = "💰 PAGO DEUDA"
            elif "FONDOS" in tipo_mov: tipo_mov = "🏦 PAGO CON FONDOS"
            
            partes_fecha = f['fecha'].split(" ")
            fecha_f = partes_fecha[0] if len(partes_fecha) > 0 else ""
            hora_f = partes_fecha[1] if len(partes_fecha) > 1 else ""
            
            datos_tabla.append({
                "Turno": st.session_state.get('turno_actual', 'NO ASIGNADO'),
                "Fecha": fecha_f,
                "Hora": hora_f,
                "Tipo": tipo_mov,
                "Cliente": f.get('cliente', '-'),
                "Productos": f.get('detalle_texto', ''),
                "Total (BS)": f['total'] if "USD" not in f['metodo'] else d['usd_en_bs'], 
                "Pagó con": " | ".join(pagos) if pagos else ("Fiado" if "CRÉDITO" in f['metodo'] else "Autopagado")
            })
        
        st.dataframe(pd.DataFrame(datos_tabla), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.write("#### 🗑️ Gestión de Facturas (Reversar Ventas)")
        st.info("Al borrar una factura, los productos vendidos volverán automáticamente al inventario de la Vitrina.")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.write("**Borrar Factura Individual:**")
            opc_f = [""] + [f"Fac #{i+1} | {f['fecha']} | {f['total']} BS" for i, f in enumerate(st.session_state.facturas)]
            fac_borrar = st.selectbox("Seleccione la factura a reversar:", opc_f)
            
            if st.button("❌ BORRAR FACTURA SELECCIONADA"):
                if fac_borrar:
                    idx = opc_f.index(fac_borrar) - 1
                    fac_eli = st.session_state.facturas[idx]
                    
                    for item in fac_eli.get('items', []):
                        for v in st.session_state.db_vitrina:
                            if v['Producto'] == item['Producto']:
                                v['Stock'] += item['Cant']
                                break
                    
                    st.session_state.facturas.pop(idx)
                    guardar_json("facturas.json", st.session_state.facturas)
                    guardar_json("vitrina.json", st.session_state.db_vitrina)
                    st.success("Factura eliminada y productos devueltos a la vitrina.")
                    st.rerun()
                    
        with col_d2:
            st.write("**Borrar TODAS las Facturas:**")
            st.warning("⚠️ Se vaciará el turno y se devolverán los productos a la vitrina.")
            if st.button("🚨 BORRAR TODAS LAS FACTURAS", type="primary"):
                for fac in st.session_state.facturas:
                    for item in fac.get('items', []):
                        for v in st.session_state.db_vitrina:
                            if v['Producto'] == item['Producto']:
                                v['Stock'] += item['Cant']
                                break
                st.session_state.facturas = []
                guardar_json("facturas.json", st.session_state.facturas)
                guardar_json("vitrina.json", st.session_state.db_vitrina)
                st.success("Se han borrado todas las facturas y recuperado el inventario.")
                st.rerun()

# ==========================================
# 7. VISTA PRINCIPAL (CAJA REGISTRADORA POS)
# ==========================================
def mostrar_pos():
    st.markdown("""<style>.total-pagar { background-color: #68A042; padding: 15px; border-radius: 5px; text-align: right; margin-bottom: 15px; color: white; font-size: 24px; font-weight: bold; } div.stButton > button { height: auto !important; min-height: 50px !important; padding: 5px 10px !important; white-space: pre-wrap !important; line-height: 1.2 !important; font-size: 14px !important; }</style>""", unsafe_allow_html=True)

    if st.session_state.get('turno_actual', 'TURNO NO ASIGNADO') == "TURNO NO ASIGNADO":
        st.error("⚠️ CAJA BLOQUEADA: AÚN NO SE HA INICIADO EL TURNO DE TRABAJO.")
        if st.button("⬅ VOLVER AL MENÚ PRINCIPAL", use_container_width=True):
            st.session_state.menu_principal = "Escritorio"; st.rerun()
        return 

    col_izq, col_der = st.columns([1.3, 1], gap="large")

    with col_izq:
        prods_con_stock = [p for p in st.session_state.db_vitrina if p["Stock"] > 0]
        cats_disponibles = sorted(list(set([p["Categoría"] for p in prods_con_stock])))
        
        # Filtro fantasma: Mostrar solo categorías con stock > 0
        if cats_disponibles:
            if 'categoria_actual' not in st.session_state or st.session_state.categoria_actual not in cats_disponibles: 
                st.session_state.categoria_actual = cats_disponibles[0]
                
            def cambiar_cat(cat): st.session_state.categoria_actual = cat
            cols_cat = st.columns(len(cats_disponibles))
            for idx, cat in enumerate(cats_disponibles):
                with cols_cat[idx % len(cats_disponibles)]:
                    st.button(cat, use_container_width=True, on_click=cambiar_cat, args=(cat,))

            st.markdown(f"<h3>Mostrando: {st.session_state.categoria_actual}</h3>", unsafe_allow_html=True)
            prods = [p for p in prods_con_stock if p["Categoría"] == st.session_state.categoria_actual]
            
            cols_prod = st.columns(3)
            for idx, prod in enumerate(prods):
                nombre, precio = prod["Producto"], prod["Precio Venta (BS)"]
                stock = prod["Stock"] - next((i['Cant'] for i in st.session_state.carrito if i['Producto'] == nombre), 0)
                with cols_prod[idx % 3]:
                    if st.button(f"{nombre}\n{precio:.2f} BS\n📦 Stock: {stock}", key=f"prod_{idx}", use_container_width=True, disabled=(stock <= 0)):
                        enc = False
                        for item in st.session_state.carrito:
                            if item["Producto"] == nombre:
                                item["Cant"] += 1; item["Total"] = item["Cant"] * item["Precio"]; enc = True; break
                        if not enc: st.session_state.carrito.append({"Producto": nombre, "Cant": 1, "Precio": precio, "Total": precio})
                        st.rerun()
        else:
            st.error("Vitrina vacía. No hay productos con stock disponible para vender.")

    with col_der:
        st.session_state.fecha_venta_manual = st.date_input("📅 Fecha de Registro (Ajustar por cortes de luz)", st.session_state.get('fecha_venta_manual', datetime.today()))
        
        st.markdown("<div style='background-color:#68A042;color:white;text-align:center;padding:10px;font-weight:bold;border-radius:5px;'>LISTA DE VENTA</div>", unsafe_allow_html=True)
        if st.session_state.carrito: st.dataframe(pd.DataFrame(st.session_state.carrito), use_container_width=True, hide_index=True)
        if st.button("🧹 LIMPIAR LISTA", use_container_width=True): st.session_state.carrito.clear(); st.rerun()
        total_pagar = sum(item['Total'] for item in st.session_state.carrito)
        st.markdown(f"<div class='total-pagar'>TOTAL A PAGAR: {total_pagar:.2f} BS</div>", unsafe_allow_html=True)

        btn_pago1, btn_pago2 = st.columns(2)
        with btn_pago1:
            if st.button("MULTIPAGO", type="primary", use_container_width=True) and st.session_state.carrito: dialogo_multipago()
        with btn_pago2:
            if st.button("TODO EFECTIVO BS", type="primary", use_container_width=True) and st.session_state.carrito: dialogo_pago_rapido("EFECTIVO")
            
        btn_pago3, btn_pago4 = st.columns(2)
        with btn_pago3:
            if st.button("TODO PAGO MÓVIL", type="primary", use_container_width=True) and st.session_state.carrito: dialogo_pago_rapido("PAGO MÓVIL")
        with btn_pago4:
            if st.button("TODO PUNTO DE VENTA", type="primary", use_container_width=True) and st.session_state.carrito: dialogo_pago_rapido("PUNTO DE VENTA")

        btn_pago5, btn_pago6 = st.columns(2)
        with btn_pago5:
            if st.button("💵 DÓLARES EFECTIVO", type="primary", use_container_width=True) and st.session_state.carrito: dialogo_pago_rapido("DÓLARES")
        with btn_pago6:
            if st.button("🤝 CRÉDITO (FIAO)", type="secondary", use_container_width=True) and st.session_state.carrito: dialogo_credito()
            
        # --- EL NUEVO BOTÓN DE PAGO CON FONDOS ---
        if st.button("🏦 PAGO CON FONDOS INTERNOS", use_container_width=True) and st.session_state.carrito: dialogo_pago_fondos()

        st.markdown("---")
        if st.button("📊 VER REPORTES Y CERRAR TURNO", use_container_width=True): st.session_state.vista = "REPORTES"; st.rerun()
        if st.button("⬅ VOLVER AL MENÚ PRINCIPAL", use_container_width=True): st.session_state.menu_principal = "Escritorio"; st.rerun()

def ejecutar():
    inicializar_estado()
    if st.session_state.vista == "POS": mostrar_pos()
    elif st.session_state.vista == "REPORTES": mostrar_reportes()
    elif st.session_state.vista == "CUENTAS_COBRAR": mostrar_cuentas_cobrar()

if __name__ == "__main__":
    ejecutar()