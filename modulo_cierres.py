import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import base64
import io
import zipfile
import glob
import os
import copy
import tempfile
import uuid

from utilidades import cargar_json, guardar_json 

try:
    from fpdf import FPDF
    FPDF_DISPONIBLE = True
except ImportError:
    FPDF_DISPONIBLE = False

# ==========================================
# 1. INICIALIZACIÓN Y RESPALDO
# ==========================================
def inicializar_estado():
    if 'tasa_bcv' not in st.session_state: 
        st.session_state.tasa_bcv = 36.50
        
    if 'historial_cierres' not in st.session_state: 
        st.session_state.historial_cierres = cargar_json("historial_cierres.json", [])
        
    if 'db_vitrina' not in st.session_state: 
        st.session_state.db_vitrina = cargar_json("vitrina.json", [])
        
    if 'db_almacen' not in st.session_state: 
        st.session_state.db_almacen = cargar_json("almacen.json", {})
        
    if 'db_recetas_fijas' not in st.session_state: 
        st.session_state.db_recetas_fijas = cargar_json("recetas.json", {})
        
    if 'cuentas_por_cobrar' not in st.session_state: 
        st.session_state.cuentas_por_cobrar = cargar_json("cuentas_cobrar.json", [])
        
    if 'db_entradas' not in st.session_state: 
        st.session_state.db_entradas = cargar_json("entradas.json", [])
        
    if 'editando_cierre_idx' not in st.session_state:
        st.session_state.editando_cierre_idx = None

def generar_respaldo_zip():
    """Comprime todos los archivos .json de la base de datos REAL en un archivo ZIP"""
    zip_buffer = io.BytesIO()
    
    rutas_posibles = [
        os.getcwd(),                                                 
        os.path.dirname(os.path.abspath(__file__)),                  
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'COMUNAPP') 
    ]
    
    archivos_a_respaldar = set()
    
    for ruta in rutas_posibles:
        if os.path.exists(ruta):
            archivos_json = glob.glob(os.path.join(ruta, "*.json"))
            for archivo in archivos_json:
                archivos_a_respaldar.add(archivo)
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        if not archivos_a_respaldar:
            zip_file.writestr("ERROR_DE_RESPALDO.txt", "No se encontraron bases de datos (.json) en el sistema.")
        else:
            for ruta_archivo in archivos_a_respaldar:
                zip_file.write(ruta_archivo, os.path.basename(ruta_archivo))
                
    return zip_buffer.getvalue()

def generar_pdf_cierre_individual(totales, df_vitrina, facturas_turno, fecha_cierre_str, turno):
    if not FPDF_DISPONIBLE: 
        return None
        
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="CIERRE DE CAJA - COMUNAPP (CORREGIDO)", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Fecha: {fecha_cierre_str} | Turno: {turno}", ln=True)
    pdf.ln(5)
    
    # SECCIÓN 1: FINANZAS
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="1. RESUMEN FINANCIERO DEL TURNO", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 8, txt=f"Efectivo Fisico: {totales.get('efectivo',0):.2f} BS", ln=True)
    pdf.cell(200, 8, txt=f"Punto de Venta: {totales.get('punto',0):.2f} BS", ln=True)
    pdf.cell(200, 8, txt=f"Pago Movil: {totales.get('pm',0):.2f} BS", ln=True)
    pdf.cell(200, 8, txt=f"Dolar Fisico: {totales.get('usd',0):.2f} $", ln=True)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 8, txt=f"TOTAL INGRESADO EN CAJA: {totales.get('real',0):.2f} BS", ln=True)
    
    pdf.set_text_color(220, 53, 69)
    pdf.cell(200, 8, txt=f"Mercancia Fiada (Creditos del turno): {totales.get('fiao',0):.2f} BS", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    
    # SECCIÓN 2: PAGOS Y FONDOS
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="2. CUENTAS PAGADAS / FONDOS", ln=True)
    pagos_deuda = [f for f in facturas_turno if "PAGO DE DEUDA" in f["metodo"] or "FONDOS" in f["metodo"]]
    
    if pagos_deuda:
        for p in pagos_deuda:
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(100, 6, txt=f"Cliente/Fondo: {str(p.get('cliente', '')).upper()}", border=0)
            pdf.cell(50, 6, txt=f"Monto: {p['total']:.2f} BS", border=0, ln=True)
            pdf.set_font("Arial", 'I', 9)
            pdf.multi_cell(0, 6, txt=f"Metodo: {p['metodo']} | Ref: {p.get('detalle_texto', '')}", border=0)
            pdf.line(10, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(2)
    else:
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 10, txt="No se registraron cobros de deudas ni uso de fondos.", ln=True)
        
    pdf.ln(5)
    
    # SECCIÓN 3: VITRINA
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="3. INVENTARIO RESTANTE (VITRINA)", ln=True)
    
    if not df_vitrina.empty:
        if 'Clasificación' in df_vitrina.columns:
            categorias = df_vitrina['Clasificación'].unique() 
        else:
            categorias = df_vitrina['Categoría'].unique()
            
        for cat in categorias:
            pdf.set_font("Arial", 'B', 11)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(190, 8, txt=f" CATEGORIA: {cat}", border=1, ln=True, fill=True)
            
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(60, 8, "Producto", 1)
            pdf.cell(26, 8, "Inicial", 1, 0, 'C')
            pdf.cell(26, 8, "Entrada", 1, 0, 'C')
            pdf.cell(26, 8, "Vendida", 1, 0, 'C')
            pdf.cell(26, 8, "Fiada", 1, 0, 'C')
            pdf.cell(26, 8, "Restante", 1, 1, 'C')
            
            pdf.set_font("Arial", size=8)
            
            col_cat = 'Clasificación' if 'Clasificación' in df_vitrina.columns else 'Categoría'
            df_cat = df_vitrina[df_vitrina[col_cat] == cat]
            
            for _, row in df_cat.iterrows():
                pdf.cell(60, 8, str(row['Producto'])[:25], 1)
                pdf.cell(26, 8, str(int(float(row['Inicial'] if pd.notna(row['Inicial']) else 0))), 1, 0, 'C')
                pdf.cell(26, 8, str(int(float(row['Entrada'] if pd.notna(row['Entrada']) else 0))), 1, 0, 'C')
                
                vendida_val = row['Vendida'] if 'Vendida' in row else row.get('Vendido', 0)
                pdf.cell(26, 8, str(int(float(vendida_val if pd.notna(vendida_val) else 0))), 1, 0, 'C')
                
                fiada_val = row['Fiada'] if 'Fiada' in row else row.get('Fiado', 0)
                pdf.cell(26, 8, str(int(float(fiada_val if pd.notna(fiada_val) else 0))), 1, 0, 'C')
                
                pdf.cell(26, 8, str(int(float(row['Restante'] if pd.notna(row['Restante']) else 0))), 1, 1, 'C')
            pdf.ln(2)
    else:
        pdf.set_font("Arial", size=10)
        pdf.cell(180, 10, txt="No se registraron movimientos en vitrina.", border=1, align='C', ln=True)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()

def generar_pdf_consolidado(fecha, tot_ef, tot_pm, tot_pt, tot_usd, tot_fiao, gran_tot_bs, gran_tot_usd, df_productos, facturas_del_dia):
    if not FPDF_DISPONIBLE: 
        return None
        
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "REPORTE CONSOLIDADO DIARIO", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Fecha: {fecha}", ln=True, align="C")
    pdf.ln(5)
    
    # Totales
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "1. INGRESOS RECAUDADOS (SUMA DE TURNOS)", ln=True)
    pdf.set_font("Arial", "", 12)
    
    pdf.cell(80, 8, "Efectivo (BS):", border=0)
    pdf.cell(0, 8, f"{tot_ef:.2f} BS", border=0, ln=True)
    
    pdf.cell(80, 8, "Pago Movil (BS):", border=0)
    pdf.cell(0, 8, f"{tot_pm:.2f} BS", border=0, ln=True)
    
    pdf.cell(80, 8, "Punto de Venta (BS):", border=0)
    pdf.cell(0, 8, f"{tot_pt:.2f} BS", border=0, ln=True)
    
    pdf.cell(80, 8, "Dolares Fisicos ($):", border=0)
    pdf.cell(0, 8, f"${tot_usd:.2f}", border=0, ln=True)
    
    pdf.set_font("Arial", "I", 12)
    pdf.set_text_color(220, 53, 69) 
    pdf.cell(80, 8, "Cuentas por Cobrar (Fiado BS):", border=0)
    pdf.cell(0, 8, f"{tot_fiao:.2f} BS", border=0, ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(80, 10, "GRAN TOTAL DEL DIA:", border=1, fill=False)
    pdf.cell(0, 10, f"${gran_tot_usd:.2f}  (Eq: {gran_tot_bs:.2f} BS)", border=1, ln=True, align="C")
    pdf.ln(10)
    
    # Tabla de Productos Detallada
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "2. COMPORTAMIENTO DEL INVENTARIO (VITRINA)", ln=True)
    
    if not df_productos.empty:
        categorias = df_productos['Clasificación'].unique()
        for cat in categorias:
            pdf.set_font("Arial", 'B', 11)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(190, 8, txt=f" CATEGORIA: {cat}", border=1, ln=True, fill=True)
            
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(40, 8, "Producto", 1)
            pdf.cell(25, 8, "Precio (BS)", 1, 0, 'C')
            pdf.cell(25, 8, "Inicial", 1, 0, 'C')
            pdf.cell(25, 8, "Entrada", 1, 0, 'C')
            pdf.cell(25, 8, "Vendido", 1, 0, 'C')
            pdf.cell(25, 8, "Fiado", 1, 0, 'C')
            pdf.cell(25, 8, "Restante", 1, 1, 'C')
            
            pdf.set_font("Arial", size=8)
            df_cat = df_productos[df_productos['Clasificación'] == cat]
            
            for _, row in df_cat.iterrows():
                pdf.cell(40, 8, str(row['Producto'])[:20], 1)
                pdf.cell(25, 8, f"{row['Precio Venta (BS)']} BS", 1, 0, 'C')
                pdf.cell(25, 8, str(int(float(row['Inicial'] if pd.notna(row['Inicial']) else 0))), 1, 0, 'C')
                pdf.cell(25, 8, str(int(float(row['Entrada'] if pd.notna(row['Entrada']) else 0))), 1, 0, 'C')
                
                vendida_val = row['Vendida'] if 'Vendida' in row else row.get('Vendido', 0)
                pdf.cell(25, 8, str(int(float(vendida_val if pd.notna(vendida_val) else 0))), 1, 0, 'C')
                
                fiada_val = row['Fiada'] if 'Fiada' in row else row.get('Fiado', 0)
                pdf.cell(25, 8, str(int(float(fiada_val if pd.notna(fiada_val) else 0))), 1, 0, 'C')
                
                pdf.cell(25, 8, str(int(float(row['Restante'] if pd.notna(row['Restante']) else 0))), 1, 1, 'C')
            pdf.ln(3)
    else:
        pdf.set_font("Arial", size=10)
        pdf.cell(180, 8, "No se registraron movimientos de inventario.", border=1, align="C", ln=True)
        
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "3. DETALLE DE FACTURAS EMITIDAS", ln=True)
    
    if facturas_del_dia:
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(20, 8, "Turno", 1)
        pdf.cell(20, 8, "Hora", 1, 0, 'C')
        pdf.cell(30, 8, "Tipo", 1, 0, 'C')
        pdf.cell(35, 8, "Cliente", 1, 0, 'C')
        pdf.cell(60, 8, "Productos", 1, 0, 'C')
        pdf.cell(25, 8, "Total", 1, 1, 'C')
        
        pdf.set_font("Arial", size=8)
        for fac in facturas_del_dia:
            partes_fecha = fac.get('fecha', '').split(" ")
            hora = partes_fecha[1] if len(partes_fecha) > 1 else ""
            tipo_mov = fac.get('metodo', '')
            
            if "DEUDA" in tipo_mov: 
                tipo_mov = "PAGO DEUDA"
            elif "FONDOS" in tipo_mov: 
                tipo_mov = "PAGO FONDOS"
                
            cliente = str(fac.get('cliente', '-'))[:15]
            detalles = str(fac.get('detalle_texto', ''))[:35]
            total = f"{float(fac.get('total', 0)):.2f}"
            
            pdf.cell(20, 8, str(fac.get('turno', 'N/A'))[:8], 1)
            pdf.cell(20, 8, hora, 1, 0, 'C')
            pdf.cell(30, 8, tipo_mov[:15], 1, 0, 'C')
            pdf.cell(35, 8, cliente, 1, 0, 'C')
            pdf.cell(60, 8, detalles, 1, 0, 'L')
            pdf.cell(25, 8, total, 1, 1, 'R')
    else:
        pdf.set_font("Arial", size=10)
        pdf.cell(180, 8, "No hay facturas registradas en esta fecha.", border=1, align="C", ln=True)

    return pdf.output(dest="S").encode("latin1")

def aplicar_css():
    st.markdown("""
        <style>
        button:has(div p:contains("VOLVER")) {
            background-color: #dc3545 !important; color: white !important; border: 2px solid #dc3545 !important;
        }
        button:has(div p:contains("VOLVER")):hover {
            background-color: #c82333 !important; border: 2px solid #c82333 !important;
        }
        </style>
    """, unsafe_allow_html=True)

def render_tarjeta_cierre(cierre_data, titulo, color_texto, index_pdf):
    if not cierre_data:
        st.info(f"⚪ {titulo}: No cerrado aún o sin datos.")
        return
        
    efectivo = cierre_data.get('efectivo_bs', 0.0)
    pm = cierre_data.get('pm_bs', 0.0)
    punto = cierre_data.get('punto_bs', 0.0)
    usd = cierre_data.get('usd_fisico', 0.0)
    fiao = cierre_data.get('fiao_bs', 0.0)
    
    tasa_actual = st.session_state.get('tasa_bcv', 36.50)
    
    total_bs_calculado = efectivo + pm + punto + (usd * tasa_actual)
    total_usd_calculado = total_bs_calculado / tasa_actual
    
    st.markdown(f"<h3 style='color:{color_texto}; margin-top:0;'>{titulo}</h3>", unsafe_allow_html=True)
    st.write(f"💵 **Efectivo (BS):** {efectivo:.2f}")
    st.write(f"📱 **Pago Móvil (BS):** {pm:.2f}")
    st.write(f"💳 **Punto de Venta (BS):** {punto:.2f}")
    st.write(f"💵 **Dólares Físicos ($):** {usd:.2f}")
    st.markdown(f"<span style='color:#dc3545;'>🤝 **Fiado (BS):** {fiao:.2f}</span>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="background-color:#d4edda; color:#155724; padding:15px; border-radius:5px; margin-top:15px; text-align:center; font-weight:bold;">
        TOTAL INGRESADO REAL<br>
        <span style="font-size: 28px; color:#1e7e34;">${total_usd_calculado:.2f} USD</span><br>
        <span style="font-size: 18px; color:#555;">(Equivalente: {total_bs_calculado:.2f} BS)</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("") 
    
    pdf_b64 = cierre_data.get('pdf_bytes_b64')
    
    if pdf_b64:
        pdf_bytes_reales = base64.b64decode(pdf_b64)
        fecha_str = cierre_data.get('fecha_hora', '').replace('/', '-').replace(':', '')
        
        st.download_button(
            label="📄 REIMPRIMIR PDF DEL TURNO", 
            data=pdf_bytes_reales, 
            file_name=f"Cierre_{fecha_str}.pdf", 
            mime="application/pdf", 
            key=f"btn_pdf_{index_pdf}", 
            use_container_width=True
        )

# ==========================================
# 3. MODO EDICIÓN DE CIERRES (MÁQUINA DEL TIEMPO)
# ==========================================
def mostrar_edicion_cierre():
    idx = st.session_state.editando_cierre_idx
    cierre = st.session_state.historial_cierres[idx]
    
    st.markdown("<h1 style='text-align: center; color: #D35400;'>✏️ MODO EDICIÓN DE CIERRE</h1>", unsafe_allow_html=True)
    st.info(f"Editando el cierre del turno **{cierre.get('turno', 'N/A')}** - Fecha: **{cierre.get('fecha_hora', '')}**")
    
    if st.button("⬅ VOLVER AL HISTORIAL (Descartar cambios)", use_container_width=True):
        st.session_state.editando_cierre_idx = None
        if 'cierre_temp' in st.session_state: 
            del st.session_state.cierre_temp
        st.rerun()
        
    # Inicializar copia temporal de trabajo con UUID para proteger borrado de facturas
    if 'cierre_temp' not in st.session_state or st.session_state.get('cierre_temp_idx') != idx:
        st.session_state.cierre_temp = copy.deepcopy(cierre)
        if "facturas_respaldo" not in st.session_state.cierre_temp:
            st.session_state.cierre_temp["facturas_respaldo"] = []
            
        # Asignar un ID único a cada factura temporal para evitar bugs al eliminar
        for f in st.session_state.cierre_temp["facturas_respaldo"]:
            if "_id" not in f:
                f["_id"] = str(uuid.uuid4())
                
        st.session_state.cierre_temp_idx = idx

    c_temp = st.session_state.cierre_temp
    fecha_cierre_str = c_temp.get("fecha", "")

    tab1, tab2 = st.tabs(["📦 Vitrina y Entradas del Día", "🧾 Gestor de Facturas Individuales"])
    
    with tab1:
        st.write("### 📦 Cuadre de Vitrina (Radiografía del Turno)")
        st.write("Modifica el **Inicial**, **Entrada**, **Vendido**, **Fiado**, **Restante**, **Precio Venta (BS)** o el **Costo (BS)**.")
        
        # LÓGICA DE CARGA DE VITRINA
        if "vitrina_snapshot" in c_temp and c_temp["vitrina_snapshot"]:
            df_vitrina_temp = pd.DataFrame(c_temp["vitrina_snapshot"])
        else:
            resumen_productos = {}
            for v in st.session_state.db_vitrina:
                nombre = v["Producto"]
                cat = v.get("Categoría", "Otros")
                stock_actual_real = v["Stock"]
                precio_venta = v.get("Precio Venta (BS)", 0.0)
                
                costo_bs = 0.0
                if nombre in st.session_state.db_recetas_fijas:
                    r = st.session_state.db_recetas_fijas[nombre]
                    c_t = sum([ing["cant"] * (st.session_state.db_almacen.get(ing["ing"], {"Costo USD": 0, "Cantidad Base": 1})["Costo USD"] / max(1, st.session_state.db_almacen.get(ing["ing"], {"Cantidad Base": 1})["Cantidad Base"])) for ing in r.get("ingredientes", [])])
                    c_u = c_t / max(1, r.get("rendimiento_tanda", 1))
                    costo_bs = (c_u * r.get("unidades_bolsa", 1)) * st.session_state.tasa_bcv
                elif nombre in st.session_state.db_almacen:
                    a = st.session_state.db_almacen[nombre]
                    costo_bs = (a.get("Costo USD", 0) / max(1, a.get("Cantidad Base", 1))) * st.session_state.tasa_bcv
                
                resumen_productos[nombre] = {
                    "Clasificación": cat, 
                    "Producto": nombre, 
                    "Costo (BS)": round(costo_bs, 2), 
                    "Precio Venta (BS)": precio_venta,
                    "Inicial": stock_actual_real, 
                    "Entrada": 0, 
                    "Vendido": 0, 
                    "Fiado": 0, 
                    "Restante": stock_actual_real
                }

            # Entradas
            for e in st.session_state.db_entradas:
                if e.get("Fecha") == fecha_cierre_str and e.get("Producto") in resumen_productos:
                    resumen_productos[e["Producto"]]["Entrada"] += e.get("Cantidad", 0)
                    
            if 'db_produccion' in st.session_state:
                for p_prod in st.session_state.db_produccion:
                    if p_prod.get("Fecha", "").startswith(fecha_cierre_str):
                        n_pan = p_prod.get("Tipo de Pan")
                        if n_pan in resumen_productos:
                            resumen_productos[n_pan]["Entrada"] += p_prod.get("Panes Producidos", 0)

            # Ventas y Fiaos
            for f in c_temp["facturas_respaldo"]:
                es_fiao = ("CRÉDITO" in f['metodo'] or "FIAO" in f['metodo'])
                for item in f.get('items', []):
                    nombre = item['Producto']
                    if nombre in resumen_productos:
                        if es_fiao: 
                            resumen_productos[nombre]["Fiado"] += item['Cant']
                        else: 
                            resumen_productos[nombre]["Vendido"] += item['Cant']
                    
            # Ajuste matemático
            for k, v in resumen_productos.items():
                v["Inicial"] = v["Restante"] + v["Vendido"] + v["Fiado"] - v["Entrada"]
                if v["Inicial"] < 0: v["Inicial"] = 0

            df_vitrina_temp = pd.DataFrame(list(resumen_productos.values()))

        st.session_state.dfs_vitrina_editados = {}
        
        if not df_vitrina_temp.empty:
            ORDEN_CATEGORIAS = ["PAN SALADO", "PAN DULCE", "REPOSTERIA", "HELADOS", "VIVERES"]
            categorias_presentes = df_vitrina_temp['Clasificación'].unique()
            cats_ordenadas = [c for c in ORDEN_CATEGORIAS if c in categorias_presentes] + [c for c in categorias_presentes if c not in ORDEN_CATEGORIAS]
            
            for cat in cats_ordenadas:
                st.markdown(f"#### 📁 {cat}")
                df_cat = df_vitrina_temp[df_vitrina_temp['Clasificación'] == cat].copy()
                df_cat = df_cat.drop(columns=['Clasificación'])
                
                df_editado = st.data_editor(
                    df_cat, 
                    disabled=["Producto"], # AHORA "Costo (BS)" ESTÁ DESBLOQUEADO
                    use_container_width=True,
                    key=f"edit_vit_{cat}_{idx}"
                )
                st.session_state.dfs_vitrina_editados[cat] = df_editado
        else:
            st.info("No hay productos en el catálogo.")

        # --- SECCIÓN ENTRADAS DEL DÍA ---
        st.write("---")
        st.write("### 🚚 Entradas de Mercancía del Día (Comercial)")
        st.info("Aquí puedes editar o eliminar el historial de compras que ingresaron en esta fecha.")
        
        if "entradas_snapshot" in c_temp:
            entradas_dia = c_temp["entradas_snapshot"]
        else:
            entradas_dia = [e for e in st.session_state.db_entradas if e.get("Fecha") == fecha_cierre_str]
            
        if entradas_dia:
            df_ent = pd.DataFrame(entradas_dia)
            df_ent_edit = st.data_editor(df_ent, key="edit_ent", use_container_width=True, num_rows="dynamic")
            st.session_state.df_entradas_editado = df_ent_edit
        else:
            st.info("No hay registro de entradas (compras de vitrina) para este día.")
            st.session_state.df_entradas_editado = pd.DataFrame()

    with tab2:
        st.write("### 🧾 Editar Facturas del Turno")
        
        col_f1, col_f2 = st.columns([3, 1])
        col_f1.info("Revisa y corrige las facturas. Puedes cambiar precios, cantidades, o eliminar la factura completa.")
        
        # --- BOTÓN PARA AGREGAR NUEVA FACTURA ---
        if col_f2.button("➕ Agregar Factura", type="secondary", use_container_width=True):
            nueva_fac = {
                "_id": str(uuid.uuid4()), # Generamos ID único para la factura nueva
                "fecha": f"{fecha_cierre_str} {datetime.now().strftime('%H:%M')}",
                "metodo": "EFECTIVO",
                "total": 0.0,
                "cliente": "",
                "desglose": {"bs_efectivo": 0.0, "bs_pagomovil": 0.0, "bs_punto": 0.0, "usd_efectivo": 0.0, "usd_en_bs": 0.0},
                "items": [{"Producto": "", "Cant": 0, "Precio": 0.0, "Total": 0.0}],
                "detalle_texto": "",
                "turno": c_temp.get("turno", "N/A")
            }
            c_temp["facturas_respaldo"].append(nueva_fac)
            st.rerun()

        facturas = c_temp["facturas_respaldo"]
        
        if not facturas:
            st.warning("Este cierre no tiene facturas guardadas en el respaldo.")
        else:
            for i, fac in enumerate(facturas):
                # Generamos llaves únicas basadas en UUID para que Streamlit no se vuelva loco al borrar
                fac_id = fac.get("_id", str(i)) 
                met_key = f"edit_met_{fac_id}"
                tot_key = f"edit_tot_{fac_id}"
                cli_key = f"edit_cli_{fac_id}"
                
                curr_met = st.session_state.get(met_key, fac.get('metodo', 'EFECTIVO'))
                curr_tot = st.session_state.get(tot_key, fac.get('total', 0.0))
                curr_cli = st.session_state.get(cli_key, fac.get('cliente', '-'))
                if curr_cli == "": curr_cli = "-"
                
                with st.expander(f"Fac #{i+1} | {curr_met} | Cliente: {curr_cli} | Total: {curr_tot} BS"):
                    c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
                    
                    metodos_posibles = [
                        "EFECTIVO", "PAGO MÓVIL", "PUNTO DE VENTA", "DÓLARES", 
                        "CRÉDITO (FIAO)", "MULTIPAGO (MIXTO)", "PAGO CON FONDOS", 
                        "PAGO DE DEUDA (EFECTIVO)", "PAGO DE DEUDA (PUNTO DE VENTA)", 
                        "PAGO DE DEUDA (PAGO MÓVIL)", "PAGO DE DEUDA (DÓLARES)"
                    ]
                    
                    metodo_actual = fac.get("metodo", "EFECTIVO")
                    idx_metodo = metodos_posibles.index(metodo_actual) if metodo_actual in metodos_posibles else 0
                    
                    nuevo_metodo = c1.selectbox("Método de Pago", metodos_posibles, index=idx_metodo, key=met_key)
                    nuevo_total = c2.number_input("Total BS", value=float(fac.get("total", 0)), key=tot_key)
                    nuevo_cliente = c3.text_input("Cliente/Concepto", value=fac.get("cliente", "") or "", key=cli_key)
                    
                    fac["metodo"] = nuevo_metodo
                    fac["total"] = nuevo_total
                    fac["cliente"] = nuevo_cliente
                    
                    # Recalcular desglose interno
                    if "EFECTIVO" in nuevo_metodo and "DÓLARES" not in nuevo_metodo and "DEUDA" not in nuevo_metodo:
                        fac["desglose"] = {"bs_efectivo": nuevo_total, "bs_pagomovil": 0.0, "bs_punto": 0.0, "usd_efectivo": 0.0, "usd_en_bs": 0.0}
                    elif "MÓVIL" in nuevo_metodo:
                        fac["desglose"] = {"bs_efectivo": 0.0, "bs_pagomovil": nuevo_total, "bs_punto": 0.0, "usd_efectivo": 0.0, "usd_en_bs": 0.0}
                    elif "PUNTO" in nuevo_metodo:
                        fac["desglose"] = {"bs_efectivo": 0.0, "bs_pagomovil": 0.0, "bs_punto": nuevo_total, "usd_efectivo": 0.0, "usd_en_bs": 0.0}
                    elif "DÓLARES" in nuevo_metodo:
                        usd_val = nuevo_total / st.session_state.tasa_bcv
                        fac["desglose"] = {"bs_efectivo": 0.0, "bs_pagomovil": 0.0, "bs_punto": 0.0, "usd_efectivo": usd_val, "usd_en_bs": nuevo_total}

                    # --- EDICIÓN DE PRODUCTOS DE LA FACTURA ---
                    st.write("**Productos Llevados (Edite cantidades, precios o elimine):**")
                    
                    items_actuales = fac.get("items", [])
                    if not items_actuales:
                        items_actuales = [{"Producto": "", "Cant": 0, "Precio": 0.0, "Total": 0.0}]
                        
                    df_items = pd.DataFrame(items_actuales)
                    
                    df_items_edit = st.data_editor(
                        df_items, 
                        key=f"edit_items_{fac_id}", 
                        num_rows="dynamic", 
                        use_container_width=True
                    )
                    
                    fac["items"] = df_items_edit.to_dict('records')
                    
                    # Manejo seguro contra nulos (NaN) al escribir el detalle
                    detalles_list = []
                    for x in fac["items"]:
                        c_val = x.get('Cant')
                        p_val = x.get('Producto')
                        
                        c_num = 0
                        if c_val is not None and str(c_val).strip() != "" and str(c_val).lower() != "nan":
                            try: c_num = int(float(c_val))
                            except: pass
                                
                        p_str = ""
                        if p_val is not None and str(p_val).strip() != "" and str(p_val).lower() != "nan":
                            p_str = str(p_val)
                            
                        if c_num > 0 or p_str:
                            detalles_list.append(f"{c_num}x {p_str}")
                            
                    fac["detalle_texto"] = ", ".join(detalles_list)
                    
                    # Botón de eliminar con llave única
                    if c4.button("🗑️ Eliminar Factura", key=f"del_fac_{fac_id}"):
                        for item in fac.get("items", []):
                            for v in st.session_state.db_vitrina:
                                if v["Producto"] == item.get("Producto"):
                                    c_val = item.get("Cant")
                                    c_num = int(float(c_val)) if c_val is not None and str(c_val).strip() != "" and str(c_val).lower() != "nan" else 0
                                    v["Stock"] += c_num
                                    break
                        facturas.pop(i)
                        st.rerun()

    st.markdown("---")
    
    if st.button("💾 GUARDAR CAMBIOS Y REGENERAR CIERRE", type="primary", use_container_width=True):
        # 1. Agrupar la Vitrina editada para la validación
        df_combined = pd.DataFrame()
        if hasattr(st.session_state, 'dfs_vitrina_editados'):
            for cat, df_edit in st.session_state.dfs_vitrina_editados.items():
                if not df_edit.empty:
                    df_edit['Clasificación'] = cat
                    df_combined = pd.concat([df_combined, df_edit], ignore_index=True)
                    
        df_combined = df_combined.fillna(0) 
        
        # --- VALIDACIONES DE DOBLE CUADRE ---
        ventas_fac = {}
        fiaos_fac = {}
        for f in c_temp["facturas_respaldo"]:
            es_fiao = ("CRÉDITO" in f['metodo'] or "FIAO" in f['metodo'])
            for item in f.get('items', []):
                p_name = item.get('Producto')
                c_val = item.get('Cant')
                c_num = int(float(c_val)) if c_val is not None and str(c_val).strip() != "" and str(c_val).lower() != "nan" else 0
                
                if p_name and str(p_name).strip() != "" and str(p_name).lower() != "nan":
                    if es_fiao:
                        fiaos_fac[p_name] = fiaos_fac.get(p_name, 0) + c_num
                    else:
                        ventas_fac[p_name] = ventas_fac.get(p_name, 0) + c_num
                    
        errores_cuadre = []
        if not df_combined.empty:
            for _, row in df_combined.iterrows():
                p_name = row["Producto"]
                
                # Conversión segura
                v_tab = int(float(row.get("Vendida", row.get("Vendido", 0))))
                f_tab = int(float(row.get("Fiada", row.get("Fiado", 0))))
                e_tab = int(float(row.get("Entrada", 0)))
                i_tab = int(float(row.get("Inicial", 0)))
                r_tab = int(float(row.get("Restante", 0)))
                
                v_fac = int(float(ventas_fac.get(p_name, 0)))
                f_fac = int(float(fiaos_fac.get(p_name, 0)))
                
                if v_tab != v_fac:
                    errores_cuadre.append(f"❌ **{p_name}**: Pusiste {v_tab} vendidos en la tabla, pero las facturas dicen {v_fac}.")
                if f_tab != f_fac:
                    errores_cuadre.append(f"❌ **{p_name}**: Pusiste {f_tab} fiados en la tabla, pero las facturas dicen {f_fac}.")
                    
                disp = i_tab + e_tab
                salida = v_tab + f_tab
                if salida > disp:
                    errores_cuadre.append(f"❌ **{p_name}**: Vendiste/fiaste {salida}, pero solo tenías {disp} (Inicial + Entrada).")
                    
                if (disp - salida) != r_tab:
                    errores_cuadre.append(f"⚠️ **{p_name}**: Matemáticas incorrectas. Inicial({i_tab}) + Entrada({e_tab}) - Salida({salida}) = {disp - salida}. Pusiste Restante: {r_tab}.")

        if errores_cuadre:
            st.error("### 🛑 Errores detectados. No se puede guardar el cierre.")
            for err in errores_cuadre:
                st.write(err)
            st.info("Por favor, corrige la tabla de la vitrina o las facturas individuales y vuelve a intentarlo.")
        else:
            # SI TODO ESTÁ BIEN, PROCEDEMOS A GUARDAR Y RECALCULAR
            if not df_combined.empty:
                c_temp["vitrina_snapshot"] = df_combined.to_dict('records')
                
                for _, row in df_combined.iterrows():
                    prod_nombre = row["Producto"]
                    nuevo_restante = int(float(row.get("Restante", 0)))
                    nuevo_precio = float(row.get("Precio Venta (BS)", 0.0))
                    
                    # Actualizar Vitrina Viva
                    for v in st.session_state.db_vitrina:
                        if v["Producto"] == prod_nombre:
                            v["Stock"] = nuevo_restante
                            v["Precio Venta (BS)"] = nuevo_precio
                            break
                            
                    # Sincronizar precio en recetas si existe
                    if prod_nombre in st.session_state.db_recetas_fijas:
                        st.session_state.db_recetas_fijas[prod_nombre]["precio_fijado_usd"] = nuevo_precio / st.session_state.tasa_bcv
            
            # 2. Aplicar edición a Entradas del Día (incluso si borra todas las filas)
            if 'df_entradas_editado' in st.session_state:
                df_ent_edit = st.session_state.df_entradas_editado
                if not df_ent_edit.empty:
                    df_ent_edit = df_ent_edit.fillna(0) # Previene NaN en entradas
                    nuevas_entradas = df_ent_edit.to_dict('records')
                else:
                    nuevas_entradas = []
                
                c_temp["entradas_snapshot"] = nuevas_entradas
                
                # Remover las entradas viejas de esta fecha y poner las editadas en la DB viva
                st.session_state.db_entradas = [e for e in st.session_state.db_entradas if e.get("Fecha") != fecha_cierre_str]
                st.session_state.db_entradas.extend(nuevas_entradas)
                guardar_json("entradas.json", st.session_state.db_entradas)

            # 3. Recalcular totales del cierre
            t_ef = 0.0
            t_pt = 0.0
            t_pm = 0.0
            t_usd = 0.0
            t_fi = 0.0
            
            for f in c_temp["facturas_respaldo"]:
                d = f.get("desglose", {})
                t_ef += float(d.get("bs_efectivo", 0))
                t_pt += float(d.get("bs_punto", 0))
                t_pm += float(d.get("bs_pagomovil", 0))
                t_usd += float(d.get("usd_efectivo", 0))
                
                if "CRÉDITO" in f["metodo"] or "FIAO" in f["metodo"]:
                    t_fi += float(f["total"])
                    
            real_bs = t_ef + t_pt + t_pm + (t_usd * st.session_state.tasa_bcv)
            
            c_temp["efectivo_bs"] = t_ef
            c_temp["punto_bs"] = t_pt
            c_temp["pm_bs"] = t_pm
            c_temp["usd_fisico"] = t_usd
            c_temp["fiao_bs"] = t_fi
            c_temp["total_bs"] = real_bs
            
            # 4. Actualizar la lista de productos resumen para la tarjeta
            prod_dict = {}
            for fac in c_temp["facturas_respaldo"]:
                for item in fac.get("items", []):
                    nombre = item.get("Producto")
                    c_val = item.get("Cant")
                    c_num = int(float(c_val)) if c_val is not None and str(c_val).strip() != "" and str(c_val).lower() != "nan" else 0
                    
                    if nombre and str(nombre).strip() != "" and str(nombre).lower() != "nan":
                        prod_dict[nombre] = prod_dict.get(nombre, 0) + c_num
                    
            c_temp["productos"] = [{"Producto": k, "Cant": v} for k, v in prod_dict.items()]
            
            # Limpiar el "_id" temporal de las facturas
            for f in c_temp["facturas_respaldo"]:
                if "_id" in f:
                    del f["_id"]
            
            # 5. Regenerar PDF
            totales_dict = {"efectivo": t_ef, "punto": t_pt, "pm": t_pm, "usd": t_usd, "fiao": t_fi, "real": real_bs}
            
            pdf_b = generar_pdf_cierre_individual(totales_dict, df_combined, c_temp["facturas_respaldo"], c_temp["fecha_hora"], c_temp.get("turno", "N/A"))
            
            if pdf_b:
                c_temp["pdf_bytes_b64"] = base64.b64encode(pdf_b).decode('utf-8')
                
            # 6. Guardar todo en disco
            st.session_state.historial_cierres[idx] = c_temp
            
            guardar_json("historial_cierres.json", st.session_state.historial_cierres)
            guardar_json("vitrina.json", st.session_state.db_vitrina)
            guardar_json("recetas.json", st.session_state.db_recetas_fijas)
            
            st.session_state.editando_cierre_idx = None
            if 'cierre_temp' in st.session_state: 
                del st.session_state.cierre_temp
                
            st.success("¡Cierre editado y recalculado exitosamente! Inventario y Caja sincronizados.")
            st.rerun()

# ==========================================
# 5. VISTA PRINCIPAL (TABS NORMALES)
# ==========================================
def mostrar_cierres():
    if st.session_state.get('editando_cierre_idx') is not None:
        mostrar_edicion_cierre()
        return

    st.markdown("<h1 style='text-align: center; color: #2c3e50;'>🔒 HISTORIAL DE CIERRES DE CAJA</h1>", unsafe_allow_html=True)
    
    if st.button("⬅ VOLVER AL MENÚ PRINCIPAL", use_container_width=True):
        st.session_state.menu_principal = "Escritorio" 
        st.rerun()
        
    tasa_actual = st.session_state.get('tasa_bcv', 36.50)
    st.write(f"**Tasa BCV de cálculo actual:** {tasa_actual:.2f} BS/$")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Resumen del Día", "🗓️ Cierre por Fecha", "📚 Historial Completo", "🍞 Volumen de Ventas"])
    
    # ---------------- TAB 1: RESUMEN DEL DÍA (Tarjetas) ----------------
    with tab1:
        st.write("### Consultar un día específico (Por Turnos)")
        fecha_consulta = st.date_input("Seleccione la Fecha:", datetime.today()).strftime("%Y-%m-%d")
        
        cierres_del_dia = [c for c in st.session_state.historial_cierres if c.get("fecha", "") == fecha_consulta]
        
        if not cierres_del_dia:
            st.warning(f"No hay cierres registrados para la fecha {fecha_consulta}.")
        else:
            col1, col2 = st.columns(2)
            cierre_manana = next((c for c in cierres_del_dia if "MAÑANA" in str(c.get("turno")).upper()), None)
            cierre_tarde = next((c for c in cierres_del_dia if "TARDE" in str(c.get("turno")).upper()), None)
            
            with col1: 
                with st.container(border=True): 
                    render_tarjeta_cierre(cierre_manana, "☀️ TURNO MAÑANA", "#5B9BD5", 1)
                    
            with col2: 
                with st.container(border=True): 
                    render_tarjeta_cierre(cierre_tarde, "🌙 TURNO TARDE", "#ED7D31", 2)
            
            tot_efectivo = sum(c.get('efectivo_bs', 0) for c in cierres_del_dia)
            tot_pm = sum(c.get('pm_bs', 0) for c in cierres_del_dia)
            tot_punto = sum(c.get('punto_bs', 0) for c in cierres_del_dia)
            tot_usd = sum(c.get('usd_fisico', 0) for c in cierres_del_dia)
            tot_fiao = sum(c.get('fiao_bs', 0) for c in cierres_del_dia)
            
            gran_total_bs = tot_efectivo + tot_pm + tot_punto + (tot_usd * tasa_actual)
            gran_total_usd = gran_total_bs / tasa_actual
            
            st.markdown(f"""
            <div style="background-color:#e8f5e9; padding:20px; border-radius:10px; border:2px solid #28a745; text-align:center; margin-top:20px;">
                <h2 style="color:#28a745; margin:0;">💰 RECAUDACIÓN GLOBAL DEL DÍA</h2>
                <div style="display:flex; justify-content: space-around; margin-top: 15px; margin-bottom: 15px; font-size: 18px;">
                    <div><b>Efectivo (BS):</b><br>{tot_efectivo:.2f}</div>
                    <div><b>Pago Móvil (BS):</b><br>{tot_pm:.2f}</div>
                    <div><b>Punto (BS):</b><br>{tot_punto:.2f}</div>
                    <div><b>Dólares ($):</b><br>{tot_usd:.2f}</div>
                    <div style='color:#dc3545;'><b>Fiado (BS):</b><br>{tot_fiao:.2f}</div>
                </div>
                <hr style="border-top: 1px solid #28a745;">
                <h3 style="color:#555; margin-bottom:0;">GRAN TOTAL INGRESADO:</h3>
                <h1 style="color:#1e7e34; margin:0; font-size:45px;">${gran_total_usd:.2f} USD</h1>
                <h3 style="color:#555; margin:0;">({gran_total_bs:.2f} BS)</h3>
            </div>
            """, unsafe_allow_html=True)

    # ---------------- TAB 2: CIERRE POR FECHA (Consolidado + Respaldo) ----------------
    with tab2:
        st.write("### 🗓️ Consolidado Diario e Inventario")
        fecha_consol = st.date_input("Seleccione la Fecha a consolidar:", datetime.today(), key="date_consol").strftime("%Y-%m-%d")
        
        cierres_fecha = [c for c in st.session_state.historial_cierres if c.get("fecha", "") == fecha_consol]
        
        if not cierres_fecha:
            st.warning(f"No hay cierres registrados para la fecha {fecha_consol}.")
        else:
            tot_ef = sum(c.get('efectivo_bs', 0) for c in cierres_fecha)
            tot_pm_consol = sum(c.get('pm_bs', 0) for c in cierres_fecha)
            tot_pt_consol = sum(c.get('punto_bs', 0) for c in cierres_fecha)
            tot_usd_consol = sum(c.get('usd_fisico', 0) for c in cierres_fecha)
            tot_fiao_consol = sum(c.get('fiao_bs', 0) for c in cierres_fecha)
            
            gran_tot_bs_c = tot_ef + tot_pm_consol + tot_pt_consol + (tot_usd_consol * tasa_actual)
            gran_tot_usd_c = gran_tot_bs_c / tasa_actual
            
            st.markdown(f"""
            <div style="background-color:#f1f8ff; padding:20px; border-radius:10px; border:1px solid #cce5ff; text-align:center;">
                <h4 style="color:#004085; margin-top:0;">📊 TOTALES RECAUDADOS ({fecha_consol})</h4>
                <div style="display:flex; justify-content: space-around; font-size: 16px; margin-top: 10px;">
                    <div><b>Efectivo (BS):</b><br>{tot_ef:.2f}</div>
                    <div><b>Pago Móvil (BS):</b><br>{tot_pm_consol:.2f}</div>
                    <div><b>Punto (BS):</b><br>{tot_pt_consol:.2f}</div>
                    <div><b>Dólares Físicos:</b><br>${tot_usd_consol:.2f}</div>
                    <div style='color:#dc3545;'><b>Cuentas p/ Cobrar:</b><br>{tot_fiao_consol:.2f} BS</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("---")
            st.write("#### 🍞 Comportamiento de la Vitrina en el Día")
            st.info("Reconstrucción de la vitrina basada en las facturas de todos los turnos del día seleccionado.")
            
            usar_snapshots = any("vitrina_snapshot" in c for c in cierres_fecha)
            resumen_productos = {}
            
            if usar_snapshots:
                for c in cierres_fecha:
                    if "vitrina_snapshot" in c and c["vitrina_snapshot"]:
                        for row in c["vitrina_snapshot"]:
                            nombre = row["Producto"]
                            if nombre not in resumen_productos:
                                resumen_productos[nombre] = {
                                    "Clasificación": row.get("Clasificación", "Otros"),
                                    "Producto": nombre,
                                    "Precio Venta (BS)": row.get("Precio Venta (BS)", 0.0),
                                    "Inicial": row.get("Inicial", 0), 
                                    "Entrada": row.get("Entrada", 0),
                                    "Vendida": row.get("Vendida", row.get("Vendido", 0)),
                                    "Fiada": row.get("Fiada", row.get("Fiado", 0)),
                                    "Restante": row.get("Restante", 0)
                                }
                            else:
                                resumen_productos[nombre]["Entrada"] += row.get("Entrada", 0)
                                resumen_productos[nombre]["Vendida"] += row.get("Vendida", row.get("Vendido", 0))
                                resumen_productos[nombre]["Fiada"] += row.get("Fiada", row.get("Fiado", 0))
                                resumen_productos[nombre]["Restante"] = row.get("Restante", 0) 
            else:
                todas_las_facturas = []
                for c in cierres_fecha:
                    if "facturas_respaldo" in c:
                        for f in c["facturas_respaldo"]:
                            f["turno"] = c.get("turno", "N/A")
                            todas_las_facturas.append(f)
                
                for f in todas_las_facturas:
                    es_fiao = ("CRÉDITO" in f['metodo'] or "FIAO" in f['metodo'])
                    for item in f.get('items', []):
                        nombre = item['Producto']
                        precio = item.get('Precio', 0.0)
                        
                        if nombre not in resumen_productos:
                            cat = "Otros"
                            stock_final = 0
                            for v in st.session_state.db_vitrina:
                                if v["Producto"] == nombre:
                                    cat = v.get("Categoría", "Otros")
                                    stock_final = v["Stock"]
                                    break
                            resumen_productos[nombre] = {
                                "Clasificación": cat, "Producto": nombre, "Precio Venta (BS)": precio,
                                "Inicial": stock_final, "Entrada": 0, "Vendida": 0, "Fiada": 0, "Restante": stock_final 
                            }
                        if es_fiao: resumen_productos[nombre]["Fiada"] += item['Cant']
                        else: resumen_productos[nombre]["Vendida"] += item['Cant']
                            
                for k, v in resumen_productos.items():
                    v["Inicial"] = v["Restante"] + v["Vendida"] + v["Fiada"]
            
            df_prod = pd.DataFrame(list(resumen_productos.values()))
            
            if not df_prod.empty:
                ORDEN_CATEGORIAS = ["PAN SALADO", "PAN DULCE", "REPOSTERIA", "HELADOS", "VIVERES"]
                df_prod['Cat_Index'] = df_prod['Clasificación'].apply(lambda x: ORDEN_CATEGORIAS.index(x) if x in ORDEN_CATEGORIAS else 99)
                df_prod = df_prod.sort_values(by=['Cat_Index', 'Producto']).drop(columns=['Cat_Index'])
                st.dataframe(df_prod, use_container_width=True, hide_index=True)
            else:
                st.info("No se registraron movimientos de productos en esta fecha.")
            
            st.write("---")
            st.write("#### 🧾 Listado de Facturas del Día")
            
            todas_las_facturas = []
            for c in cierres_fecha:
                if "facturas_respaldo" in c:
                    for f in c["facturas_respaldo"]:
                        f["turno"] = c.get("turno", "N/A")
                        todas_las_facturas.append(f)
                        
            if todas_las_facturas:
                datos_f = []
                for f in todas_las_facturas:
                    d = f.get('desglose', {})
                    p = [f"Ef:{d.get('bs_efectivo',0)}" if d.get('bs_efectivo',0)>0 else "", 
                         f"Pto:{d.get('bs_punto',0)}" if d.get('bs_punto',0)>0 else "", 
                         f"PM:{d.get('bs_pagomovil',0)}" if d.get('bs_pagomovil',0)>0 else "", 
                         f"USD:${d.get('usd_efectivo',0)}" if d.get('usd_efectivo',0)>0 else ""]
                    
                    tm = "💰 PAGO DEUDA" if "DEUDA" in f['metodo'] else ("🏦 PAGO FONDOS" if "FONDOS" in f['metodo'] else f['metodo'])
                    
                    partes_f = f['fecha'].split(" ")
                    hora_f = partes_f[1] if len(partes_f) > 1 else ""
                    
                    datos_f.append({
                        "Turno": f.get('turno', 'N/A'), 
                        "Hora": hora_f, 
                        "Tipo": tm, 
                        "Cliente": f.get('cliente', '-'),
                        "Productos": f.get('detalle_texto', ''), 
                        "Total (BS)": f['total'] if "USD" not in f['metodo'] else d.get('usd_en_bs', 0),
                        "Pagó con": " | ".join(filter(None, p)) if p else ("Fiado" if "CRÉDITO" in tm else "Autopagado")
                    })
                st.dataframe(pd.DataFrame(datos_f), use_container_width=True, hide_index=True)
            else:
                st.info("No hay facturas guardadas en el respaldo.")
            
            st.write("")
            pdf_bytes = generar_pdf_consolidado(fecha_consol, tot_ef, tot_pm_consol, tot_pt_consol, tot_usd_consol, tot_fiao_consol, gran_tot_bs_c, gran_tot_usd_c, df_prod, todas_las_facturas)
            
            st.download_button(
                label="📄 DESCARGAR REPORTE DETALLADO (PDF) DE ESTA FECHA", 
                data=pdf_bytes, 
                file_name=f"Reporte_Consolidado_Detallado_{fecha_consol}.pdf", 
                mime="application/pdf", 
                use_container_width=True
            )
                
        st.write("---")
        st.write("### 💾 Respaldo de Seguridad del Sistema")
        try:
            zip_data = generar_respaldo_zip()
            st.download_button(
                label="📦 DESCARGAR RESPALDO COMPLETO (.ZIP)", 
                data=zip_data, 
                file_name=f"Respaldo_COMUNAPP_{datetime.now().strftime('%d_%m_%Y')}.zip", 
                mime="application/zip", 
                type="primary", 
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error generando respaldo. Detalle: {e}")

    # ---------------- TAB 3: HISTORIAL COMPLETO ----------------
    with tab3:
        st.write("### 🗄️ Todos los Cierres Registrados")
        if not st.session_state.historial_cierres:
            st.info("La bóveda está vacía. Aún no se han cerrado turnos.")
        else:
            for i, cierre in enumerate(reversed(st.session_state.historial_cierres)):
                real_idx = len(st.session_state.historial_cierres) - 1 - i
                fecha_hora = cierre.get('fecha_hora', 'Sin fecha')
                turno = cierre.get('turno', 'N/A')
                total_real = cierre.get('total_bs', 0)
                
                with st.expander(f"🧾 {fecha_hora} | {turno} | Total Ingresado: {total_real:.2f} BS"):
                    c_ef, c_pt, c_pm, c_fi = st.columns(4)
                    c_ef.metric("Efectivo (BS)", f"{cierre.get('efectivo_bs', 0):.2f}")
                    c_pt.metric("Punto (BS)", f"{cierre.get('punto_bs', 0):.2f}")
                    c_pm.metric("P. Móvil (BS)", f"{cierre.get('pm_bs', 0):.2f}")
                    c_fi.metric("Fiao (BS)", f"{cierre.get('fiao_bs', 0):.2f}")
                    
                    pdf_b64 = cierre.get('pdf_bytes_b64')
                    if pdf_b64:
                        pdf_bytes_dl = base64.b64decode(pdf_b64)
                        st.download_button("📄 Descargar Reporte PDF", data=pdf_bytes_dl, file_name=f"Reporte_{fecha_hora.replace('/', '-')}.pdf", mime="application/pdf", key=f"dl_hist_{i}")
                        
                    st.markdown("---")
                    
                    # --- BOTÓN DE EDICIÓN MÁQUINA DEL TIEMPO ---
                    if st.button("✏️ Editar Cierre (Corregir Facturas e Inventario)", type="primary", key=f"edit_{real_idx}"):
                        if cierre.get("distribuido", False):
                            st.error("⚠️ Este cierre ya fue distribuido en FONDOS. Ve a Ingresos, reversa la distribución primero y luego intenta editarlo aquí.")
                        else:
                            st.session_state.editando_cierre_idx = real_idx
                            st.rerun()

    # ---------------- TAB 4: VOLUMEN DE VENTAS ----------------
    with tab4:
        st.write("### 📊 ¿Cuánto producto está saliendo en total?")
        filtro_tiempo = st.radio("Rango de tiempo:", ["Hoy", "Últimos 7 días", "Este Mes"], horizontal=True)
        
        hoy = datetime.today()
        
        if filtro_tiempo == "Hoy": 
            fecha_inicio = hoy.strftime("%Y-%m-%d")
        elif filtro_tiempo == "Últimos 7 días": 
            fecha_inicio = (hoy - timedelta(days=7)).strftime("%Y-%m-%d")
        else: 
            fecha_inicio = hoy.replace(day=1).strftime("%Y-%m-%d")
            
        cierres_filtrados = [c for c in st.session_state.historial_cierres if c.get("fecha", "") >= fecha_inicio and c.get("fecha", "") <= hoy.strftime("%Y-%m-%d")]
        
        if not cierres_filtrados:
            st.info("No hay ventas en este rango de tiempo.")
        else:
            todos_los_productos = []
            for cierre in cierres_filtrados:
                todos_los_productos.extend(cierre.get("productos", []))
                
            if todos_los_productos:
                df_prod = pd.DataFrame(todos_los_productos)
                if not df_prod.empty and 'Producto' in df_prod.columns and 'Cant' in df_prod.columns:
                    df_agrupado = df_prod.groupby("Producto")["Cant"].sum().reset_index()
                    df_agrupado = df_agrupado.sort_values(by="Cant", ascending=False)
                    st.write(f"**Cantidades totales vendidas ({filtro_tiempo}):**")
                    st.dataframe(df_agrupado, use_container_width=True, hide_index=True)
                else:
                    st.write("No hay detalle de productos para estos cierres.")

# ==========================================
# 4. CONTROLADOR
# ==========================================
def ejecutar():
    inicializar_estado()
    aplicar_css()
    mostrar_cierres()

if __name__ == "__main__":
    ejecutar()