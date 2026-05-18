import streamlit as st
import pandas as pd
from datetime import datetime
import tempfile
import copy
from utilidades import cargar_json, guardar_json 

try:
    from fpdf import FPDF
    FPDF_DISPONIBLE = True
except ImportError:
    FPDF_DISPONIBLE = False

# ==========================================
# 1. INICIALIZACIÓN Y AUTO-REPARACIÓN
# ==========================================
def inicializar_estado_inventario():
    if 'vista_inv' not in st.session_state:
        st.session_state.vista_inv = "MENU"
        
    if 'tasa_bcv' not in st.session_state:
        st.session_state.tasa_bcv = 36.50 
        
    if 'db_vitrina' not in st.session_state:
        st.session_state.db_vitrina = cargar_json("vitrina.json", [])
        
    # Base de datos predeterminada para Almacén dividida por Tipos (Sin Stock Actual)
    db_almacen_default = {
        # --- ALMACÉN DE PRODUCCIÓN (MATERIA PRIMA) ---
        "HARINA DE TRIGO": {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": 45000, "Costo USD": 43.00},
        "AZÚCAR": {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": 50000, "Costo USD": 48.00},
        "SAL": {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": 20000, "Costo USD": 25.00},
        "MANTEQUILLA": {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": 20000, "Costo USD": 26.00},
        "LEVADURA": {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": 500, "Costo USD": 5.00},
        "MANTECA": {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": 5000, "Costo USD": 26.00},
        "NATA": {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": 3800, "Costo USD": 6.50},
        "HUEVOS": {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": 30, "Costo USD": 7.188}, 
        "CANELA": {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": 1000, "Costo USD": 15.00},
        "ANIS": {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": 1000, "Costo USD": 16.00},
        "VAINILLA": {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": 500, "Costo USD": 18.00},
        "GUAYABA": {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": 5000, "Costo USD": 21.00},
        "AREQUIPE": {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": 5000, "Costo USD": 30.00},
        "LECHE LÍQUIDA": {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": 1000, "Costo USD": 2.88},
        "RELAX": {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": 1000, "Costo USD": 8.00},
        "QUESO": {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": 3000, "Costo USD": 7.00},
        "VARIADOS (MEZCLA)": {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": 1000, "Costo USD": 5.10},
        
        # --- ALMACÉN VITRINA (MERCANCÍA COMERCIAL) ---
        "LOTE TETAS": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 32, "Costo USD": 15.00},
        "LOTE PALETAS": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 30, "Costo USD": 5.00},
        "LOTE BAMBIS": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 24, "Costo USD": 2.30},
        "CAJA MALTA": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 36, "Costo USD": 11.00},
        "CAJA REFRESCO": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 24, "Costo USD": 17.28},
        "LOTE GALLETAS": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 3, "Costo USD": 2.247},
        "CAJA CHICLES": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 4, "Costo USD": 0.224},
        "LOTE BUBALOO": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 5, "Costo USD": 0.134},
        "LOTE DESODORANTE": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 3, "Costo USD": 0.359},
        "LOTE TIP TOP": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 1, "Costo USD": 0.224},
        "LOTE BIANCHI": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 1, "Costo USD": 0.629},
        "LOTE LAILA": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 11, "Costo USD": 0.179},
        "LOTE FREEGEL": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 4, "Costo USD": 0.269},
        "LOTE MAXCOCO": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 2, "Costo USD": 0.561},
        "LOTE CHESTREES": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 3, "Costo USD": 0.786},
        "LOTE PEPITO RIK": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 5, "Costo USD": 0.674},
        "LOTE BOOKA": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 1, "Costo USD": 0.449},
        "LOTE OREO": {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": 1, "Costo USD": 0.674}
    }
    
    if 'db_almacen' not in st.session_state:
        st.session_state.db_almacen = cargar_json("almacen.json", db_almacen_default)
        
    modificado_alm = False
    para_produccion = ["HARINA DE TRIGO", "AZÚCAR", "SAL", "MANTEQUILLA", "LEVADURA", "MANTECA", "NATA", "HUEVOS", "CANELA", "ANIS", "VAINILLA", "GUAYABA", "AREQUIPE", "LECHE LÍQUIDA", "RELAX", "QUESO", "VARIADOS (MEZCLA)"]
    for k, v in st.session_state.db_almacen.items():
        if "Cantidad Base" not in v:
            v["Cantidad Base"] = v.get("Cantidad", 1000)
            modificado_alm = True
        if "Tipo" not in v:
            v["Tipo"] = "ALMACÉN DE PRODUCCIÓN" if k in para_produccion else "ALMACÉN VITRINA"
            modificado_alm = True
        if "Stock Actual" in v:
            del v["Stock Actual"]
            modificado_alm = True
            
    if modificado_alm: guardar_json("almacen.json", st.session_state.db_almacen)
        
    recetas_maestras = {
        "PAN FRANCÉS": {"categoria": "PAN SALADO", "ingredientes": [{"ing": "HARINA DE TRIGO", "cant": 2000}, {"ing": "AZÚCAR", "cant": 600}, {"ing": "SAL", "cant": 30}, {"ing": "MANTEQUILLA", "cant": 800}, {"ing": "LEVADURA", "cant": 20}], "rendimiento_tanda": 53, "unidades_bolsa": 10, "precio_fijado_usd": 0.55},
        "PAN CAMPESINO": {"categoria": "PAN SALADO", "ingredientes": [{"ing": "HARINA DE TRIGO", "cant": 2000}, {"ing": "AZÚCAR", "cant": 600}, {"ing": "SAL", "cant": 30}, {"ing": "MANTEQUILLA", "cant": 800}, {"ing": "LEVADURA", "cant": 20}], "rendimiento_tanda": 9, "unidades_bolsa": 1, "precio_fijado_usd": 0.56},
        "PAN DE QUESO": {"categoria": "PAN SALADO", "ingredientes": [{"ing": "MANTECA", "cant": 300}, {"ing": "VAINILLA", "cant": 70}, {"ing": "NATA", "cant": 70}, {"ing": "AZÚCAR", "cant": 850}, {"ing": "SAL", "cant": 12}, {"ing": "HARINA DE TRIGO", "cant": 3200}, {"ing": "HUEVOS", "cant": 6}, {"ing": "LEVADURA", "cant": 30}, {"ing": "CANELA", "cant": 10}, {"ing": "ANIS", "cant": 10}, {"ing": "QUESO", "cant": 100}], "rendimiento_tanda": 14, "unidades_bolsa": 1, "precio_fijado_usd": 1.57},
        "PAN ANDINO": {"categoria": "PAN DULCE", "ingredientes": [{"ing": "MANTECA", "cant": 300}, {"ing": "VAINILLA", "cant": 70}, {"ing": "NATA", "cant": 70}, {"ing": "AZÚCAR", "cant": 850}, {"ing": "SAL", "cant": 12}, {"ing": "HARINA DE TRIGO", "cant": 3200}, {"ing": "HUEVOS", "cant": 6}, {"ing": "LEVADURA", "cant": 30}, {"ing": "CANELA", "cant": 10}, {"ing": "ANIS", "cant": 10}, {"ing": "GUAYABA", "cant": 150}], "rendimiento_tanda": 9, "unidades_bolsa": 1, "precio_fijado_usd": 1.68},
        "PAN DE GUAYABA": {"categoria": "PAN DULCE", "ingredientes": [{"ing": "MANTECA", "cant": 300}, {"ing": "VAINILLA", "cant": 70}, {"ing": "NATA", "cant": 70}, {"ing": "AZÚCAR", "cant": 850}, {"ing": "SAL", "cant": 12}, {"ing": "HARINA DE TRIGO", "cant": 3200}, {"ing": "HUEVOS", "cant": 6}, {"ing": "LEVADURA", "cant": 30}, {"ing": "CANELA", "cant": 10}, {"ing": "ANIS", "cant": 10}, {"ing": "GUAYABA", "cant": 150}], "rendimiento_tanda": 14, "unidades_bolsa": 1, "precio_fijado_usd": 1.57},
        "PAN DE GUAYABA CON QUESO": {"categoria": "PAN DULCE", "ingredientes": [{"ing": "MANTECA", "cant": 300}, {"ing": "VAINILLA", "cant": 70}, {"ing": "NATA", "cant": 70}, {"ing": "AZÚCAR", "cant": 850}, {"ing": "SAL", "cant": 12}, {"ing": "HARINA DE TRIGO", "cant": 3200}, {"ing": "HUEVOS", "cant": 6}, {"ing": "LEVADURA", "cant": 30}, {"ing": "CANELA", "cant": 10}, {"ing": "ANIS", "cant": 10}, {"ing": "GUAYABA", "cant": 75}, {"ing": "QUESO", "cant": 75}], "rendimiento_tanda": 14, "unidades_bolsa": 1, "precio_fijado_usd": 1.57},
        "PAN AZUCARADO": {"categoria": "PAN DULCE", "ingredientes": [{"ing": "MANTECA", "cant": 300}, {"ing": "VAINILLA", "cant": 70}, {"ing": "NATA", "cant": 70}, {"ing": "AZÚCAR", "cant": 850}, {"ing": "SAL", "cant": 12}, {"ing": "HARINA DE TRIGO", "cant": 3200}, {"ing": "HUEVOS", "cant": 6}, {"ing": "LEVADURA", "cant": 30}, {"ing": "CANELA", "cant": 10}, {"ing": "ANIS", "cant": 10}], "rendimiento_tanda": 14, "unidades_bolsa": 1, "precio_fijado_usd": 1.01},
        "VARIADOS": {"categoria": "PAN DULCE", "ingredientes": [{"ing": "MANTECA", "cant": 300}, {"ing": "VAINILLA", "cant": 70}, {"ing": "NATA", "cant": 70}, {"ing": "AZÚCAR", "cant": 850}, {"ing": "SAL", "cant": 12}, {"ing": "HARINA DE TRIGO", "cant": 3200}, {"ing": "HUEVOS", "cant": 6}, {"ing": "LEVADURA", "cant": 30}, {"ing": "CANELA", "cant": 10}, {"ing": "ANIS", "cant": 10}, {"ing": "GUAYABA", "cant": 150}, {"ing": "VARIADOS (MEZCLA)", "cant": 950}], "rendimiento_tanda": 95, "unidades_bolsa": 10, "precio_fijado_usd": 1.00},
        "PAN DE AREQUIPE": {"categoria": "PAN DULCE", "ingredientes": [{"ing": "MANTECA", "cant": 300}, {"ing": "VAINILLA", "cant": 70}, {"ing": "NATA", "cant": 70}, {"ing": "AZÚCAR", "cant": 850}, {"ing": "SAL", "cant": 12}, {"ing": "HARINA DE TRIGO", "cant": 3200}, {"ing": "HUEVOS", "cant": 6}, {"ing": "LEVADURA", "cant": 30}, {"ing": "CANELA", "cant": 10}, {"ing": "ANIS", "cant": 10}, {"ing": "AREQUIPE", "cant": 100}], "rendimiento_tanda": 14, "unidades_bolsa": 1, "precio_fijado_usd": 1.57},
        "PASTA SECA": {"categoria": "REPOSTERIA", "ingredientes": [{"ing": "MANTEQUILLA", "cant": 550}, {"ing": "AZÚCAR", "cant": 375}, {"ing": "LECHE LÍQUIDA", "cant": 200}, {"ing": "NATA", "cant": 5}, {"ing": "VAINILLA", "cant": 5}, {"ing": "HARINA DE TRIGO", "cant": 750}], "rendimiento_tanda": 200, "unidades_bolsa": 1, "precio_fijado_usd": 0.06},
        "PALMERITAS GRANDES": {"categoria": "REPOSTERIA", "ingredientes": [{"ing": "SAL", "cant": 120}, {"ing": "MANTEQUILLA", "cant": 10}, {"ing": "HARINA DE TRIGO", "cant": 120}, {"ing": "RELAX", "cant": 2}, {"ing": "MANTECA", "cant": 80}], "rendimiento_tanda": 25, "unidades_bolsa": 1, "precio_fijado_usd": 1.01},
        "PALMERITAS PEQUEÑAS": {"categoria": "REPOSTERIA", "ingredientes": [{"ing": "SAL", "cant": 15}, {"ing": "MANTEQUILLA", "cant": 13}, {"ing": "HARINA DE TRIGO", "cant": 150}, {"ing": "RELAX", "cant": 26}, {"ing": "MANTECA", "cant": 106}], "rendimiento_tanda": 19, "unidades_bolsa": 1, "precio_fijado_usd": 0.78},
        "PASTELES GRANDES": {"categoria": "REPOSTERIA", "ingredientes": [{"ing": "SAL", "cant": 20}, {"ing": "MANTEQUILLA", "cant": 16}, {"ing": "HARINA DE TRIGO", "cant": 200}, {"ing": "RELAX", "cant": 33}, {"ing": "MANTECA", "cant": 133}], "rendimiento_tanda": 15, "unidades_bolsa": 1, "precio_fijado_usd": 1.01},
        "PASTELES PEQUEÑOS": {"categoria": "REPOSTERIA", "ingredientes": [{"ing": "SAL", "cant": 75}, {"ing": "MANTEQUILLA", "cant": 6}, {"ing": "HARINA DE TRIGO", "cant": 75}, {"ing": "RELAX", "cant": 1}, {"ing": "MANTECA", "cant": 50}], "rendimiento_tanda": 40, "unidades_bolsa": 1, "precio_fijado_usd": 0.78}
    }
    
    db_recetas = cargar_json("recetas.json", {})
    modificado_rec = False
    for prod, datos in recetas_maestras.items():
        if prod not in db_recetas or "categoria" not in db_recetas[prod] or "precio_fijado_usd" not in db_recetas[prod]:
            db_recetas[prod] = datos
            modificado_rec = True
            
    if modificado_rec:
        guardar_json("recetas.json", db_recetas)
        
    st.session_state.db_recetas_fijas = db_recetas
    
    if 'db_entradas' not in st.session_state:
        st.session_state.db_entradas = cargar_json("entradas.json", [])
    if 'db_produccion' not in st.session_state:
        st.session_state.db_produccion = cargar_json("produccion.json", [])

def aplicar_css_botones():
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

def generar_pdf_tabla(titulo_reporte, dataframe):
    if not FPDF_DISPONIBLE: return None
    pdf = FPDF(orientation='L') 
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt="PANADERIA COMUNAL LANCEROS ATURES", ln=True, align='C')
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, txt=titulo_reporte, ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, txt=f"Fecha de impresion: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)
    
    if dataframe.empty:
        pdf.cell(0, 10, txt="No hay datos para mostrar.", ln=True, align='C')
    else:
        ancho_columna = 270 / len(dataframe.columns)
        pdf.set_font("Arial", 'B', 9)
        for col in dataframe.columns:
            pdf.cell(ancho_columna, 8, txt=str(col)[:20], border=1, align='C')
        pdf.ln()
        
        pdf.set_font("Arial", '', 9)
        for _, row in dataframe.iterrows():
            for col in dataframe.columns:
                valor = str(row[col])[:30].encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(ancho_columna, 8, txt=valor, border=1, align='C')
            pdf.ln()
            
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()

# ==========================================
# 2. VISTAS DE LOS SUBMÓDULOS 
# ==========================================

def mostrar_vitrina():
    st.markdown("<h2 style='text-align: center; color: #ED7D31;'>🏪 VITRINA (Inventario Actual Comercial)</h2>", unsafe_allow_html=True)
    
    if st.session_state.db_vitrina:
        df_vitrina = pd.DataFrame(st.session_state.db_vitrina)
        df_vitrina = df_vitrina.rename(columns={"Categoría": "Clasificación"})
        
        clasificaciones_vitrina = sorted(list(df_vitrina["Clasificación"].unique()))
        filtro_cat = st.selectbox("🔍 Filtrar por Clasificación:", ["TODAS LAS CLASIFICACIONES"] + clasificaciones_vitrina)
        
        if filtro_cat != "TODAS LAS CLASIFICACIONES":
            df_vitrina = df_vitrina[df_vitrina["Clasificación"] == filtro_cat]
        
        df_vitrina = df_vitrina[["Clasificación", "Producto", "Stock", "Precio Venta (BS)"]]
        st.dataframe(df_vitrina, use_container_width=True, hide_index=True)
        
        total_bs = (df_vitrina["Stock"] * df_vitrina["Precio Venta (BS)"]).sum()
        total_usd = total_bs / st.session_state.tasa_bcv
        st.info(f"💰 **Valor estimado de venta de la mercancía mostrada:** {total_bs:.2f} BS (Equivalente a ${total_usd:.2f} USD)")
        
        if FPDF_DISPONIBLE and not df_vitrina.empty:
            pdf_data = generar_pdf_tabla("INVENTARIO DE VITRINA", df_vitrina)
            st.download_button("📄 Imprimir Vitrina en PDF", data=pdf_data, file_name="Vitrina.pdf", mime="application/pdf", use_container_width=True)
            
        # --- EDICIÓN DIRECTA DE STOCK Y PRECIO EN VITRINA ---
        st.markdown("<div style='padding: 15px; border-radius: 8px; border: 1px solid #b8daff; background-color: #e8f4f8; margin-top: 15px;'>", unsafe_allow_html=True)
        st.write("##### ✏️ Corregir Stock y Precio en Vitrina")
        prod_a_editar = st.selectbox("Seleccione el producto a corregir:", [""] + [p["Producto"] for p in st.session_state.db_vitrina], key="edit_vit")
        if prod_a_editar:
            item_actual = next((x for x in st.session_state.db_vitrina if x["Producto"] == prod_a_editar), None)
            col_e1, col_e2, col_e3 = st.columns([1, 1, 1])
            nuevo_stock = col_e1.number_input("Stock Real Exacto:", min_value=0, value=int(item_actual["Stock"]), step=1)
            nuevo_precio_bs = col_e2.number_input("Precio Venta (BS):", min_value=0.0, value=float(item_actual.get("Precio Venta (BS)", 0.0)), step=1.0)
            
            if col_e3.button("💾 Actualizar Datos", type="primary", use_container_width=True):
                item_actual["Stock"] = nuevo_stock
                item_actual["Precio Venta (BS)"] = round(nuevo_precio_bs, 2)
                guardar_json("vitrina.json", st.session_state.db_vitrina)
                
                # Sincronizar con Recetas/Almacén si existe allí
                if prod_a_editar in st.session_state.db_recetas_fijas:
                    nuevo_precio_usd = nuevo_precio_bs / st.session_state.tasa_bcv
                    st.session_state.db_recetas_fijas[prod_a_editar]["precio_fijado_usd"] = nuevo_precio_usd
                    guardar_json("recetas.json", st.session_state.db_recetas_fijas)
                    
                st.success(f"Stock y Precio de '{prod_a_editar}' actualizados con éxito.")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='padding: 15px; border-radius: 8px; border: 1px solid #f5c6cb; background-color: #f8d7da; margin-top: 15px;'>", unsafe_allow_html=True)
        st.write("##### 🗑️ Eliminar Producto de la Vitrina")
        prod_a_borrar = st.selectbox("Seleccione el producto a eliminar permanentemente:", [""] + [p["Producto"] for p in st.session_state.db_vitrina])
        if st.button("❌ Eliminar Producto", type="primary"):
            if prod_a_borrar:
                st.session_state.db_vitrina = [p for p in st.session_state.db_vitrina if p["Producto"] != prod_a_borrar]
                guardar_json("vitrina.json", st.session_state.db_vitrina)
                st.success(f"Producto '{prod_a_borrar}' eliminado con éxito de la vitrina.")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
    else:
        st.warning("La vitrina está vacía. Registre entradas o producción para comenzar.")
    
    st.write("")
    if st.button("⬅ VOLVER A INVENTARIO", use_container_width=True):
        st.session_state.vista_inv = "MENU"
        st.rerun()

def mostrar_entradas():
    st.markdown("<h2 style='text-align: center; color: #4CAF50;'>📦 ENTRADA DE PRODUCTOS A VITRINA</h2>", unsafe_allow_html=True)
    st.info("💡 Usa este módulo SOLO para mercancía comercial directa a Vitrina (Víveres, Helados, Refrescos). La materia prima se ingresa en el Almacén de Producción.")
    
    tab1, tab2 = st.tabs(["📝 Registrar Entrada a Vitrina", "📊 Consolidado de Entradas"])
    
    with tab1:
        fecha_compra = st.date_input("Día de Entrada", datetime.today())
        
        categoria = st.selectbox("Clasificación", ["VIVERES", "HELADOS", "OTRA CATEGORÍA (Escribir abajo)"])
        if categoria == "OTRA CATEGORÍA (Escribir abajo)":
            categoria = st.text_input("Escriba la nueva categoría").upper()
            
        producto_final = st.text_input("Nombre del Artículo (Ej: COCA-COLA 2L)")
        
        col3, col4, col5 = st.columns(3)
        cantidad = col3.number_input("Cantidad (Unidades/Empaques)", min_value=1, step=1)
        precio_costo = col4.number_input("Costo Unitario (BS)", min_value=0.0, step=0.01)
        precio_venta = col5.number_input("Venta Unitario (BS)", min_value=0.0, step=0.01)
        
        if st.button("💾 REGISTRAR ENTRADA Y ENVIAR A VITRINA", type="primary", use_container_width=True):
            if producto_final:
                producto_final = producto_final.strip().upper()
                st.session_state.db_entradas.append({
                    "Fecha": fecha_compra.strftime("%Y-%m-%d"), "Categoría": categoria, "Producto": producto_final,
                    "Cantidad": cantidad, "Costo Unitario": precio_costo, "Precio Venta": precio_venta, "Costo Total": cantidad * precio_costo
                })
                
                prod_existente = False
                for item in st.session_state.db_vitrina:
                    if item["Producto"] == producto_final:
                        item["Stock"] += cantidad
                        item["Precio Venta (BS)"] = precio_venta 
                        item["Categoría"] = categoria 
                        item["Entradas_Turno"] = item.get("Entradas_Turno", 0) + cantidad
                        prod_existente = True
                        break
                if not prod_existente:
                    st.session_state.db_vitrina.append({"Producto": producto_final, "Categoría": categoria, "Stock": cantidad, "Precio Venta (BS)": precio_venta, "Entradas_Turno": cantidad})
                
                guardar_json("entradas.json", st.session_state.db_entradas)
                guardar_json("vitrina.json", st.session_state.db_vitrina)
                st.success(f"¡Se registró exitosamente en Vitrina bajo la clasificación {categoria}!")
            else:
                st.error("Ingrese el nombre del producto.")
                    
    with tab2:
        if st.session_state.db_entradas:
            df_entradas = pd.DataFrame(st.session_state.db_entradas)
            st.dataframe(df_entradas, use_container_width=True, hide_index=True)
            
            if FPDF_DISPONIBLE:
                pdf_data = generar_pdf_tabla("CONSOLIDADO DE ENTRADAS DE MERCANCIA", df_entradas)
                st.download_button("📄 Imprimir Entradas en PDF", data=pdf_data, file_name="Entradas.pdf", mime="application/pdf", use_container_width=True)

            st.markdown("---")
            opciones_e = [f"Reg #{i+1} | {e['Producto']} (Cant: {e['Cantidad']})" for i, e in enumerate(st.session_state.db_entradas)]
            seleccion_e = st.selectbox("Modificar registro:", opciones_e)
            if seleccion_e:
                idx_e = opciones_e.index(seleccion_e)
                reg_e = st.session_state.db_entradas[idx_e]
                afectar_vitrina_e = st.checkbox("☑️ Reversar stock en Vitrina", value=False)
                if st.button("🗑️ Borrar Registro de Entrada", use_container_width=True):
                    if afectar_vitrina_e:
                        for item in st.session_state.db_vitrina:
                            if item["Producto"] == reg_e['Producto']:
                                item["Stock"] = max(0, item["Stock"] - reg_e['Cantidad'])
                                item["Entradas_Turno"] = max(0, item.get("Entradas_Turno", 0) - reg_e['Cantidad'])
                    st.session_state.db_entradas.pop(idx_e)
                    guardar_json("entradas.json", st.session_state.db_entradas)
                    guardar_json("vitrina.json", st.session_state.db_vitrina)
                    st.rerun()

    st.write("")
    if st.button("⬅ VOLVER A INVENTARIO", use_container_width=True):
        st.session_state.vista_inv = "MENU"
        st.rerun()


def mostrar_materia_prima():
    st.markdown("<h2 style='text-align: center; color: #9C27B0;'>🥖 ALMACÉN, COSTOS Y RECETAS</h2>", unsafe_allow_html=True)
    st.write(f"**Tasa BCV del Sistema:** {st.session_state.tasa_bcv:.2f} BS/$")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🏭 Almacén Producción", "🏪 Almacén Vitrina (Lotes)", "📖 Gestor de Recetas", "📁 Precios y Rentabilidad"])
    
    # ---------------- TAB 1: ALMACÉN PRODUCCIÓN (MATERIA PRIMA) ----------------
    with tab1:
        st.write("### 🌾 Inventario de Materia Prima")
        st.write("Aquí gestionas los insumos para calcular recetas. Los costos puedes ingresarlos en Bolívares o Dólares y se actualizarán con la Tasa BCV.")
        
        items_produccion = {k:v for k,v in st.session_state.db_almacen.items() if v.get("Tipo") == "ALMACÉN DE PRODUCCIÓN"}
        
        if items_produccion:
            tabla_alm_prod = []
            for ing, datos in items_produccion.items():
                costo_usd = datos["Costo USD"]
                costo_bs = costo_usd * st.session_state.tasa_bcv
                costo_g_usd = costo_usd / datos["Cantidad Base"]
                tabla_alm_prod.append({
                    "Ingrediente": ing, 
                    "Tamaño Saco (gr/ml)": datos["Cantidad Base"], 
                    "Costo Saco (BS)": f"{costo_bs:.2f} BS",
                    "Costo Saco ($)": f"${costo_usd:.2f}", 
                    "Costo Unitario ($)": f"${costo_g_usd:.6f}"
                })
            df_alm_prod = pd.DataFrame(tabla_alm_prod)
            st.dataframe(df_alm_prod, use_container_width=True, hide_index=True)
            
            if FPDF_DISPONIBLE and not df_alm_prod.empty:
                pdf_alm_p = generar_pdf_tabla("ALMACEN DE PRODUCCION (MATERIA PRIMA)", df_alm_prod)
                st.download_button("📄 Imprimir Almacén Producción (PDF)", data=pdf_alm_p, file_name="Almacen_Produccion.pdf", mime="application/pdf")
            
            st.write("#### 🔄 Actualizar Precios y Empaques")
            col_a1, col_a2, col_a3 = st.columns(3)
            ing_a_actualizar = col_a1.selectbox("Seleccione ingrediente:", list(items_produccion.keys()), key="sel_ing_prod")
            datos_sel = items_produccion[ing_a_actualizar]
            
            moneda_costo = col_a2.radio("Moneda del Costo:", ["Bolívares (BS)", "Dólares ($)"], key="mon_cost_prod")
            if moneda_costo == "Bolívares (BS)":
                nuevo_costo = col_a2.number_input(f"Actualizar Costo Total (BS):", value=float(datos_sel['Costo USD'] * st.session_state.tasa_bcv), step=10.0)
                nuevo_costo_usd_final = nuevo_costo / st.session_state.tasa_bcv
            else:
                nuevo_costo = col_a2.number_input(f"Actualizar Costo Total ($):", value=float(datos_sel['Costo USD']), step=1.0)
                nuevo_costo_usd_final = nuevo_costo
                
            nueva_cantidad_base = col_a3.number_input("Actualizar Tamaño Saco (gr/ml):", value=float(datos_sel['Cantidad Base']), step=100.0)
            
            if st.button("💾 Actualizar Almacén de Producción", type="primary"):
                st.session_state.db_almacen[ing_a_actualizar]['Costo USD'] = nuevo_costo_usd_final
                st.session_state.db_almacen[ing_a_actualizar]['Cantidad Base'] = nueva_cantidad_base
                guardar_json("almacen.json", st.session_state.db_almacen) 
                st.success("¡Almacén de Producción actualizado!")
                st.rerun()

        st.markdown("<div style='padding: 15px; border-radius: 8px; border: 1px solid #b8daff; background-color: #cce5ff; margin-top: 15px;'>", unsafe_allow_html=True)
        st.write("##### ➕ Agregar Nueva Materia Prima al Catálogo")
        c_n1, c_n2, c_n3 = st.columns(3)
        n_nombre = c_n1.text_input("Nombre del Ingrediente", key="nn_prod")
        n_cant = c_n2.number_input("Peso/Cantidad Base (gr/ml)", min_value=1.0, value=1000.0, key="nc_prod")
        n_costo = c_n3.number_input("Costo del Empaque ($ USD)", min_value=0.01, value=10.0, key="nco_prod")
        if st.button("Crear Ingrediente", type="primary", key="btn_crear_prod"):
            if n_nombre:
                st.session_state.db_almacen[n_nombre.upper()] = {"Tipo": "ALMACÉN DE PRODUCCIÓN", "Cantidad Base": n_cant, "Costo USD": n_costo}
                guardar_json("almacen.json", st.session_state.db_almacen)
                st.success(f"Materia Prima '{n_nombre.upper()}' creada.")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- TAB 2: ALMACÉN COMERCIAL (VITRINA/LOTES) ----------------
    with tab2:
        st.write("### 🏪 Inventario Base Comercial (Lotes, Cajas)")
        st.write("Aquí gestionas precios y empaques base de insumos que no se cocinan, como Cajas de Maltas, Lotes de Helados, etc.")
        
        items_comercial = {k:v for k,v in st.session_state.db_almacen.items() if v.get("Tipo") == "ALMACÉN VITRINA"}
        
        if items_comercial:
            tabla_alm_com = []
            for ing, datos in items_comercial.items():
                costo_usd = datos["Costo USD"]
                costo_bs = costo_usd * st.session_state.tasa_bcv
                costo_g_usd = costo_usd / datos["Cantidad Base"]
                tabla_alm_com.append({
                    "Producto/Lote": ing, 
                    "Unidades por Lote": datos["Cantidad Base"], 
                    "Costo del Lote (BS)": f"{costo_bs:.2f} BS",
                    "Costo del Lote ($)": f"${costo_usd:.2f}", 
                    "Costo Unitario ($)": f"${costo_g_usd:.6f}"
                })
            df_alm_com = pd.DataFrame(tabla_alm_com)
            st.dataframe(df_alm_com, use_container_width=True, hide_index=True)
            
            if FPDF_DISPONIBLE and not df_alm_com.empty:
                pdf_alm_c = generar_pdf_tabla("ALMACEN VITRINA (LOTES COMERCIALES)", df_alm_com)
                st.download_button("📄 Imprimir Almacén Vitrina (PDF)", data=pdf_alm_c, file_name="Almacen_Vitrina.pdf", mime="application/pdf")
            
            st.write("#### 🔄 Actualizar Precios y Empaques Comerciales")
            col_v1, col_v2, col_v3 = st.columns(3)
            ing_v_actualizar = col_v1.selectbox("Seleccione producto/lote:", list(items_comercial.keys()), key="sel_ing_vit")
            datos_v_sel = items_comercial[ing_v_actualizar]
            
            moneda_costo_v = col_v2.radio("Moneda del Costo:", ["Bolívares (BS)", "Dólares ($)"], key="mon_cost_vit")
            if moneda_costo_v == "Bolívares (BS)":
                nuevo_costo_v = col_v2.number_input(f"Actualizar Costo Total (BS):", value=float(datos_v_sel['Costo USD'] * st.session_state.tasa_bcv), step=10.0)
                nuevo_costo_v_usd_final = nuevo_costo_v / st.session_state.tasa_bcv
            else:
                nuevo_costo_v = col_v2.number_input(f"Actualizar Costo Total ($):", value=float(datos_v_sel['Costo USD']), step=1.0)
                nuevo_costo_v_usd_final = nuevo_costo_v
            
            nueva_cantidad_base_v = col_v3.number_input("Actualizar Unidades por Lote:", value=float(datos_v_sel['Cantidad Base']), step=1.0)
            
            if st.button("💾 Actualizar Lote Comercial", type="primary"):
                st.session_state.db_almacen[ing_v_actualizar]['Costo USD'] = nuevo_costo_v_usd_final
                st.session_state.db_almacen[ing_v_actualizar]['Cantidad Base'] = nueva_cantidad_base_v
                guardar_json("almacen.json", st.session_state.db_almacen) 
                st.success("¡Almacén Comercial actualizado permanentemente!")
                st.rerun()

        st.markdown("<div style='padding: 15px; border-radius: 8px; border: 1px solid #b8daff; background-color: #cce5ff; margin-top: 15px;'>", unsafe_allow_html=True)
        st.write("##### ➕ Agregar Nuevo Lote Comercial al Catálogo")
        c_n1_v, c_n2_v, c_n3_v = st.columns(3)
        n_nombre_v = c_n1_v.text_input("Nombre del Lote (Ej: CAJA JUGO)", key="nn_vit")
        n_cant_v = c_n2_v.number_input("Unidades por Lote", min_value=1.0, value=12.0, key="nc_vit")
        n_costo_v = c_n3_v.number_input("Costo del Lote ($ USD)", min_value=0.01, value=5.0, key="nco_vit")
        if st.button("Crear Lote Comercial", type="primary", key="btn_crear_vit"):
            if n_nombre_v:
                st.session_state.db_almacen[n_nombre_v.upper()] = {"Tipo": "ALMACÉN VITRINA", "Cantidad Base": n_cant_v, "Costo USD": n_costo_v}
                guardar_json("almacen.json", st.session_state.db_almacen)
                st.success(f"Lote Comercial '{n_nombre_v.upper()}' creado.")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- TAB 3: GESTOR DE RECETAS ----------------
    with tab3:
        st.write("### 📖 Configurador de Recetas")
        modo_receta = st.radio("Modo:", ["Editar Existente", "Crear Nueva Receta", "Transferir Receta", "Eliminar Receta"], horizontal=True)
        
        if modo_receta == "Editar Existente":
            cat_sel = st.selectbox("1. Clasificación:", ["PAN SALADO", "PAN DULCE", "REPOSTERIA"])
            prods = [p for p, d in st.session_state.db_recetas_fijas.items() if d.get("categoria") == cat_sel]
            if prods:
                pan_sel = st.selectbox("2. Producto a editar:", prods)
                receta = st.session_state.db_recetas_fijas[pan_sel]
                
                st.write(f"**Ingredientes actuales de {pan_sel}:**")
                for i, ing in enumerate(receta["ingredientes"]):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c1.write(f"- {ing['ing']}")
                    nuevo_cant = c2.number_input("Cantidad (gr/und):", value=float(ing['cant']), key=f"ing_{pan_sel}_{i}")
                    receta["ingredientes"][i]["cant"] = nuevo_cant
                    if c3.button("🗑️ Eliminar", key=f"del_{pan_sel}_{i}"):
                        receta["ingredientes"].pop(i)
                        guardar_json("recetas.json", st.session_state.db_recetas_fijas); st.rerun()
                
                st.write("**Añadir nuevo ingrediente a esta receta:**")
                cn1, cn2, cn3 = st.columns([2, 1, 1])
                mat_prima = [k for k, v in st.session_state.db_almacen.items() if v.get("Tipo") == "ALMACÉN DE PRODUCCIÓN"]
                nuevo_ing_nombre = cn1.selectbox("Ingrediente:", [""] + mat_prima, key=f"n_ing_{pan_sel}")
                nuevo_ing_cant = cn2.number_input("Cantidad a usar:", min_value=1, key=f"n_cant_{pan_sel}")
                if cn3.button("➕ Añadir Ing.", key=f"btn_add_{pan_sel}"):
                    if nuevo_ing_nombre:
                        receta["ingredientes"].append({"ing": nuevo_ing_nombre, "cant": nuevo_ing_cant})
                        guardar_json("recetas.json", st.session_state.db_recetas_fijas); st.rerun()
                        
                st.write("---")
                col_r1, col_r2 = st.columns(2)
                nuevo_rend = col_r1.number_input("¿Cuántos panes salen de esta mezcla completa? (Rendimiento por Tanda):", min_value=1, value=int(receta.get("rendimiento_tanda", 1)))
                receta["rendimiento_tanda"] = nuevo_rend
                if st.button("💾 GUARDAR RECETA", type="primary"):
                    guardar_json("recetas.json", st.session_state.db_recetas_fijas)
                    st.success("Receta actualizada exitosamente.")
                
                if FPDF_DISPONIBLE:
                    df_r = pd.DataFrame(receta["ingredientes"]).rename(columns={"ing": "Ingrediente", "cant": "Cantidad (Gr/Und)"})
                    pdf_r = generar_pdf_tabla(f"RECETA: {pan_sel} (Rinde {nuevo_rend} unds)", df_r)
                    st.download_button(f"📄 Imprimir Receta: {pan_sel}", data=pdf_r, file_name=f"Receta_{pan_sel}.pdf", mime="application/pdf")
                    
            else:
                st.warning("No hay productos registrados en esta categoría.")
            
        elif modo_receta == "Crear Nueva Receta":
            cat_nueva = st.selectbox("Clasificación del nuevo pan/producto:", ["PAN SALADO", "PAN DULCE", "REPOSTERIA"])
            nombre_nuevo = st.text_input("Nombre de la nueva receta (Ej: PAN DE QUESO ESPECIAL):").upper()
            if st.button("Crear Receta en Blanco", type="primary"):
                if nombre_nuevo and nombre_nuevo not in st.session_state.db_recetas_fijas:
                    st.session_state.db_recetas_fijas[nombre_nuevo] = {
                        "categoria": cat_nueva, "ingredientes": [], "rendimiento_tanda": 1, "unidades_bolsa": 1, "precio_fijado_usd": 1.0
                    }
                    guardar_json("recetas.json", st.session_state.db_recetas_fijas)
                    st.success("Receta creada. Ve a 'Editar Existente' para agregarle los ingredientes.")
                    st.rerun()
                else:
                    st.error("Nombre inválido o la receta ya existe.")
                    
        elif modo_receta == "Transferir Receta":
            st.write("#### 🔄 Transferir / Duplicar Receta")
            st.info("Copia una receta existente para crear una nueva sin tener que meter los ingredientes uno por uno.")
            c_orig, c_dest = st.columns(2)
            cat_origen = c_orig.selectbox("1. Clasificación Origen:", ["PAN SALADO", "PAN DULCE", "REPOSTERIA"], key="cat_orig")
            prods_origen = [p for p, d in st.session_state.db_recetas_fijas.items() if d.get("categoria") == cat_origen]
            
            if prods_origen:
                pan_origen = c_orig.selectbox("2. Receta a copiar:", prods_origen)
                cat_destino = c_dest.selectbox("3. Clasificación Destino:", ["PAN SALADO", "PAN DULCE", "REPOSTERIA"], key="cat_dest")
                pan_destino = c_dest.text_input("4. Nombre del NUEVO Pan:").upper()
                
                if st.button("🔄 DUPLICAR RECETA", type="primary", use_container_width=True):
                    if pan_destino and pan_destino not in st.session_state.db_recetas_fijas:
                        nueva_receta = copy.deepcopy(st.session_state.db_recetas_fijas[pan_origen])
                        nueva_receta["categoria"] = cat_destino
                        st.session_state.db_recetas_fijas[pan_destino] = nueva_receta
                        guardar_json("recetas.json", st.session_state.db_recetas_fijas)
                        st.success(f"Receta '{pan_origen}' copiada a '{pan_destino}' exitosamente.")
                        st.rerun()
                    else:
                        st.error("Ingrese un nombre válido y que no exista actualmente.")
            else:
                st.warning("No hay recetas en la categoría de origen.")
                
        elif modo_receta == "Eliminar Receta":
            st.write("#### 🗑️ Eliminar Receta")
            cat_elim = st.selectbox("1. Clasificación a buscar:", ["PAN SALADO", "PAN DULCE", "REPOSTERIA"], key="cat_elim")
            prods_elim = [p for p, d in st.session_state.db_recetas_fijas.items() if d.get("categoria") == cat_elim]
            
            if prods_elim:
                pan_elim = st.selectbox("2. Receta a eliminar:", prods_elim)
                st.warning(f"⚠️ ¿Está seguro que desea eliminar la receta de '{pan_elim}' de la base de datos? Esta acción no se puede deshacer.")
                if st.button("❌ ELIMINAR RECETA DEFINITIVAMENTE", type="primary"):
                    del st.session_state.db_recetas_fijas[pan_elim]
                    guardar_json("recetas.json", st.session_state.db_recetas_fijas)
                    st.success(f"Receta '{pan_elim}' eliminada exitosamente.")
                    st.rerun()
            else:
                st.warning("No hay recetas en esta categoría para eliminar.")

    # ---------------- TAB 4: PRECIOS Y RENTABILIDAD ----------------
    with tab4:
        st.write("### 💵 Análisis Financiero y Precios de Venta")
        cat_p = st.selectbox("Clasificación a Analizar:", ["PAN SALADO", "PAN DULCE", "REPOSTERIA"], key="cat_p")
        prods_p = [p for p, d in st.session_state.db_recetas_fijas.items() if d.get("categoria") == cat_p]
        
        if prods_p:
            # BOTON PDF PARA TODA LA CLASIFICACIÓN
            st.write("#### 🖨️ Reportes Financieros Masivos")
            if FPDF_DISPONIBLE:
                datos_cat_pdf = []
                for p_name in prods_p:
                    p_datos = st.session_state.db_recetas_fijas[p_name]
                    c_t = sum([ing["cant"] * (st.session_state.db_almacen.get(ing["ing"], {"Costo USD": 0, "Cantidad Base": 1})["Costo USD"] / st.session_state.db_almacen.get(ing["ing"], {"Costo USD": 0, "Cantidad Base": 1})["Cantidad Base"]) for ing in p_datos["ingredientes"]])
                    c_u = c_t / max(1, p_datos.get("rendimiento_tanda", 1))
                    c_b = c_u * p_datos.get("unidades_bolsa", 1)
                    p_v = p_datos.get("precio_fijado_usd", 0.0)
                    g_v = p_v - c_b
                    datos_cat_pdf.append({
                        "Producto": p_name,
                        "Costo Empaque (BS)": f"{c_b * st.session_state.tasa_bcv:.2f}",
                        "Precio Venta (BS)": f"{p_v * st.session_state.tasa_bcv:.2f}",
                        "Ganancia Neta (BS)": f"{g_v * st.session_state.tasa_bcv:.2f}"
                    })
                df_cat_pdf = pd.DataFrame(datos_cat_pdf)
                pdf_cat_b = generar_pdf_tabla(f"RENTABILIDAD GLOBAL: {cat_p}", df_cat_pdf)
                st.download_button(f"📄 Imprimir Análisis Completo de {cat_p}", data=pdf_cat_b, file_name=f"Rentabilidad_{cat_p}.pdf", mime="application/pdf", use_container_width=True)
            
            st.write("---")
            pan_p = st.selectbox("Seleccione Producto Específico para Ajustar Precio:", prods_p, key="pan_p")
            datos_pan = st.session_state.db_recetas_fijas[pan_p]
            
            costo_tanda_usd = 0.0
            for ing in datos_pan["ingredientes"]:
                nombre_i = ing["ing"]
                datos_alm = st.session_state.db_almacen.get(nombre_i, {"Costo USD": 0, "Cantidad Base": 1})
                costo_g = datos_alm["Costo USD"] / datos_alm["Cantidad Base"]
                costo_tanda_usd += (ing["cant"] * costo_g)
                
            costo_unitario_usd = costo_tanda_usd / max(1, datos_pan.get("rendimiento_tanda", 1))
            
            st.info(f"**Costo Mezcla:** ${costo_tanda_usd:.4f} | **Costo de 1 pan:** ${costo_unitario_usd:.4f}")
            
            c_p1, c_p2 = st.columns(2)
            und_bolsa = c_p1.number_input("Panes por Empaque/Bolsa (Venta)", min_value=1, value=int(datos_pan.get("unidades_bolsa", 1)))
            costo_bolsa_usd = costo_unitario_usd * und_bolsa
            
            # --- INPUT EN BOLÍVARES ---
            precio_guardado_usd = float(datos_pan.get("precio_fijado_usd", costo_bolsa_usd * 1.3))
            precio_manual_bs = c_p2.number_input("Fijar Precio de Venta al Público (En BOLÍVARES)", min_value=0.0, value=precio_guardado_usd * st.session_state.tasa_bcv, step=1.0)
            
            precio_manual_usd = precio_manual_bs / st.session_state.tasa_bcv
            
            ganancia_usd = precio_manual_usd - costo_bolsa_usd
            if precio_manual_usd > 0:
                pct_costo = (costo_bolsa_usd / precio_manual_usd) * 100
                pct_ganancia = (ganancia_usd / precio_manual_usd) * 100
            else:
                pct_costo, pct_ganancia = 0, 0
                
            df_analisis_pan = pd.DataFrame([
                {"Concepto": "Precio de Venta", "Monto $": f"${precio_manual_usd:.3f}", "En BS": f"{precio_manual_bs:.2f} BS", "%": "100%"},
                {"Concepto": "Costo de Producción", "Monto $": f"${costo_bolsa_usd:.3f}", "En BS": f"{costo_bolsa_usd * st.session_state.tasa_bcv:.2f} BS", "%": f"{pct_costo:.2f}%"},
                {"Concepto": "Ganancia Neta", "Monto $": f"${ganancia_usd:.3f}", "En BS": f"{ganancia_usd * st.session_state.tasa_bcv:.2f} BS", "%": f"{pct_ganancia:.2f}%"}
            ])
            st.table(df_analisis_pan)
            
            col_g1, col_g2 = st.columns(2)
            if col_g1.button("💾 GUARDAR PRECIO", type="primary", use_container_width=True):
                st.session_state.db_recetas_fijas[pan_p]["unidades_bolsa"] = und_bolsa
                st.session_state.db_recetas_fijas[pan_p]["precio_fijado_usd"] = precio_manual_usd
                for item in st.session_state.db_vitrina:
                    if item["Producto"] == pan_p: item["Precio Venta (BS)"] = round(precio_manual_bs, 2); break
                guardar_json("recetas.json", st.session_state.db_recetas_fijas)
                guardar_json("vitrina.json", st.session_state.db_vitrina)
                st.success(f"Precio actualizado a {round(precio_manual_bs, 2)} BS en Vitrina.")
                
            if FPDF_DISPONIBLE:
                pdf_p_single = generar_pdf_tabla(f"ANALISIS FINANCIERO: {pan_p}", df_analisis_pan)
                col_g2.download_button("📄 Imprimir Análisis de este Pan", data=pdf_p_single, file_name=f"Analisis_{pan_p}.pdf", mime="application/pdf", use_container_width=True)
                
    st.write("")
    if st.button("⬅ VOLVER A INVENTARIO", use_container_width=True):
        st.session_state.vista_inv = "MENU"
        st.rerun()

def mostrar_produccion():
    st.markdown("<h2 style='text-align: center; color: #2196F3;'>👨‍🍳 PRODUCCIÓN (Hornadas del Día)</h2>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🍞 Registrar Producción", "📈 Historial y Facturas de Insumos"])
    
    with tab1:
        st.write("Al registrar la producción, el sistema **calculará la materia prima teórica** de la receta para su historial y enviará los panes a la Vitrina Comercial.")
        categoria_prod = st.selectbox("1. Clasificación:", ["PAN SALADO", "PAN DULCE", "REPOSTERIA"])
        productos = sorted([prod for prod, datos in st.session_state.db_recetas_fijas.items() if datos.get("categoria") == categoria_prod])
        
        pan_producido = st.selectbox("2. Producto Horneado", productos if productos else ["Vacío"])
        
        with st.form("form_produccion"):
            fecha_prod = st.date_input("Día de Producción", datetime.today())
            panes_a_vitrina = st.number_input("¿Cuántos PANES EXACTOS salieron del horno?", min_value=1, step=1, value=1)
            
            st.info("💡 El sistema calculará automáticamente la materia prima consumida basándose en la proporción de la receta, pero **NO descontará nada** del almacén de costos.")
            
            if st.form_submit_button("✅ REGISTRAR HORNEADA Y ENVIAR A VITRINA", use_container_width=True):
                if not productos or pan_producido == "Vacío":
                    st.error("Seleccione un producto válido.")
                else:
                    receta = st.session_state.db_recetas_fijas[pan_producido]
                    rendimiento_teorico = receta.get("rendimiento_tanda", 1)
                    
                    factor_proporcion = panes_a_vitrina / rendimiento_teorico
                    
                    insumos_usados = []
                    
                    # 1. Calcular Insumos Teóricos (Solo para registro)
                    for ing in receta["ingredientes"]:
                        nombre_ing = ing["ing"]
                        cant_usar = ing["cant"] * factor_proporcion
                        insumos_usados.append({"Ingrediente": nombre_ing, "Cant Usada": round(cant_usar, 2)})
                    
                    # 2. Enviar a Vitrina
                    encontrado = False
                    for item in st.session_state.db_vitrina:
                        if item["Producto"] == pan_producido:
                            item["Stock"] += panes_a_vitrina
                            item["Entradas_Turno"] = item.get("Entradas_Turno", 0) + panes_a_vitrina
                            encontrado = True; break
                            
                    if not encontrado:
                        precio_bs = receta.get("precio_fijado_usd", 0) * st.session_state.tasa_bcv
                        st.session_state.db_vitrina.append({"Producto": pan_producido, "Categoría": categoria_prod, "Stock": panes_a_vitrina, "Precio Venta (BS)": round(precio_bs, 2), "Entradas_Turno": panes_a_vitrina})
                    
                    # 3. Guardar "Factura" de Producción
                    st.session_state.db_produccion.append({
                        "Fecha": fecha_prod.strftime("%Y-%m-%d %H:%M"),
                        "Tipo de Pan": pan_producido,
                        "Panes Producidos": panes_a_vitrina,
                        "Insumos Consumidos": insumos_usados
                    })
                    
                    guardar_json("vitrina.json", st.session_state.db_vitrina)
                    guardar_json("produccion.json", st.session_state.db_produccion)
                    st.success(f"¡Horneada lista! Se enviaron exactamente {panes_a_vitrina} '{pan_producido}' a la vitrina.")

    with tab2:
        if st.session_state.db_produccion:
            st.write("### 🧾 Historial de Producción Teórica")
            for i, prod in enumerate(reversed(st.session_state.db_produccion)):
                with st.expander(f"📅 {prod['Fecha']} | {prod['Panes Producidos']} panes creados de {prod['Tipo de Pan']}"):
                    st.write("**Material Directo Calculado por el Sistema:**")
                    st.table(pd.DataFrame(prod["Insumos Consumidos"]))
                    
                    idx_real = len(st.session_state.db_produccion) - 1 - i
                    if st.button("🗑️ Reversar Producción (Anular Panes de Vitrina)", key=f"del_prod_{idx_real}"):
                        # Anular Panes de Vitrina
                        for item in st.session_state.db_vitrina:
                            if item["Producto"] == prod['Tipo de Pan']:
                                item["Stock"] = max(0, item["Stock"] - prod['Panes Producidos'])
                                item["Entradas_Turno"] = max(0, item.get("Entradas_Turno", 0) - prod['Panes Producidos'])
                        
                        # Borrar Registro
                        st.session_state.db_produccion.pop(idx_real)
                        
                        guardar_json("vitrina.json", st.session_state.db_vitrina)
                        guardar_json("produccion.json", st.session_state.db_produccion)
                        st.rerun()
        else:
            st.info("No hay producciones registradas.")

    st.write("")
    if st.button("⬅ VOLVER A INVENTARIO", use_container_width=True):
        st.session_state.vista_inv = "MENU"
        st.rerun()

# ==========================================
# 4. MENÚ PRINCIPAL
# ==========================================
def mostrar_menu_inventario():
    st.markdown("<h1 style='text-align: center; color: #28a745;'>📦 MÓDULO DE INVENTARIO Y COSTOS</h1>", unsafe_allow_html=True)
    st.write("")
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("""<div style="background-color: #fdf2e9; padding: 20px; border-radius: 10px; border: 2px solid #ED7D31; text-align: center; margin-bottom: 10px;"><h3 style="color: #ED7D31; margin:0;">🏪 VITRINA COMERCIAL</h3><p style="color: #555; font-size: 14px;">Inventario físico listo para vender</p></div>""", unsafe_allow_html=True)
        if st.button("ENTRAR A VITRINA", use_container_width=True): st.session_state.vista_inv = "VITRINA"; st.rerun()
        st.write("")
        st.markdown("""<div style="background-color: #f3e5f5; padding: 20px; border-radius: 10px; border: 2px solid #9C27B0; text-align: center; margin-bottom: 10px;"><h3 style="color: #9C27B0; margin:0;">🥖 ALMACÉN, COSTOS Y RECETAS</h3><p style="color: #555; font-size: 14px;">Materia Prima y Configuración de Panes</p></div>""", unsafe_allow_html=True)
        if st.button("VER ALMACÉN Y RECETAS", use_container_width=True): st.session_state.vista_inv = "MATERIA_PRIMA"; st.rerun()

    with col2:
        st.markdown("""<div style="background-color: #e8f5e9; padding: 20px; border-radius: 10px; border: 2px solid #4CAF50; text-align: center; margin-bottom: 10px;"><h3 style="color: #4CAF50; margin:0;">📦 ENTRADA PRODUCTOS</h3><p style="color: #555; font-size: 14px;">Ingreso directo de Víveres y Helados a Vitrina</p></div>""", unsafe_allow_html=True)
        if st.button("REGISTRAR ENTRADAS", use_container_width=True): st.session_state.vista_inv = "ENTRADAS"; st.rerun()
        st.write("")
        st.markdown("""<div style="background-color: #e3f2fd; padding: 20px; border-radius: 10px; border: 2px solid #2196F3; text-align: center; margin-bottom: 10px;"><h3 style="color: #2196F3; margin:0;">👨‍🍳 PRODUCCIÓN</h3><p style="color: #555; font-size: 14px;">Calcula receta y envía panes a Vitrina</p></div>""", unsafe_allow_html=True)
        if st.button("REGISTRAR PRODUCCIÓN", use_container_width=True): st.session_state.vista_inv = "PRODUCCION"; st.rerun()

    st.markdown("---")
    st.write("")
    if st.button("⬅ VOLVER AL MENÚ PRINCIPAL", use_container_width=True):
        st.session_state.menu_principal = "Escritorio"; st.session_state.vista_inv = "MENU"; st.rerun()

# ==========================================
# 5. EJECUCIÓN
# ==========================================
def ejecutar():
    inicializar_estado_inventario()
    aplicar_css_botones() 
    if st.session_state.vista_inv == "MENU": mostrar_menu_inventario()
    elif st.session_state.vista_inv == "VITRINA": mostrar_vitrina()
    elif st.session_state.vista_inv == "ENTRADAS": mostrar_entradas()
    elif st.session_state.vista_inv == "MATERIA_PRIMA": mostrar_materia_prima()
    elif st.session_state.vista_inv == "PRODUCCION": mostrar_produccion()

if __name__ == "__main__":
    ejecutar()