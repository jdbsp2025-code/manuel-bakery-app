import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import tempfile
from utilidades import obtener_ruta_datos # <-- IMPORTAMOS LA RUTA SEGURA

try:
    from fpdf import FPDF
    FPDF_DISPONIBLE = True
except ImportError:
    FPDF_DISPONIBLE = False

def generar_pdf_tasas(dataframe):
    if not FPDF_DISPONIBLE: return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt="PANADERIA COMUNAL LANCEROS ATURES", ln=True, align='C')
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, txt="HISTORIAL DE TASAS DE CAMBIO", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, txt=f"Fecha de impresion: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)
    
    if dataframe.empty:
        pdf.cell(0, 10, txt="No hay datos registrados en el historial.", ln=True, align='C')
    else:
        ancho_col = 190 / 3
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(ancho_col, 10, txt="Fecha", border=1, align='C')
        pdf.cell(ancho_col, 10, txt="Hora de Registro", border=1, align='C')
        pdf.cell(ancho_col, 10, txt="Tasa (BS/$)", border=1, align='C', ln=True)
        pdf.set_font("Arial", '', 10)
        for _, row in dataframe.iterrows():
            pdf.cell(ancho_col, 10, txt=str(row['Fecha']), border=1, align='C')
            pdf.cell(ancho_col, 10, txt=str(row['Hora']), border=1, align='C')
            pdf.cell(ancho_col, 10, txt=f"{row['Tasa_Bs']:.2f} BS", border=1, align='C', ln=True)
            
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()

def ejecutar():
    st.markdown("""<style>button:has(div p:contains("Volver al Panel Principal")) {background-color: #dc3545 !important; color: white !important; border: 2px solid #dc3545 !important;}button:has(div p:contains("Volver al Panel Principal")):hover {background-color: #c82333 !important; border: 2px solid #c82333 !important;}</style>""", unsafe_allow_html=True)
    st.markdown(f"<h1 style='text-align: center; color: #2196F3;'>💱 GESTIÓN DE TASAS DE CAMBIO</h1>", unsafe_allow_html=True)
    
    if st.button("⬅️ Volver al Panel Principal", use_container_width=True):
        st.session_state.menu_principal = "Escritorio"
        st.rerun()
    st.write("---")

    # --- AHORA USAMOS LA RUTA SEGURA PARA NO PERDER DATOS ---
    archivo_tasas = obtener_ruta_datos("historial_tasas.csv")

    if os.path.exists(archivo_tasas):
        df = pd.read_csv(archivo_tasas)
    else:
        df = pd.DataFrame(columns=["Fecha", "Hora", "Tasa_Bs"])

    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    if fecha_hoy not in df['Fecha'].values:
        nueva_tasa = {"Fecha": fecha_hoy, "Hora": datetime.now().strftime("%I:%M %p"), "Tasa_Bs": st.session_state.get('tasa_bcv', 36.50)}
        df_nuevo = pd.DataFrame([nueva_tasa])
        df = pd.concat([df_nuevo, df], ignore_index=True)
        df.to_csv(archivo_tasas, index=False)
        st.toast(f"✅ Tasa de hoy ({st.session_state.tasa_bcv}) guardada automáticamente")

    df['Fecha_DT'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y', errors='coerce')
    col_izq, col_der = st.columns([1, 1.5], gap="large")

    with col_izq:
        st.markdown(f"""<div style="background-color:#e3f2fd; padding:20px; border-radius:10px; border:2px solid #2196F3; text-align:center; margin-bottom:20px;"><h4 style="color:#1565C0; margin-top:0;">Tasa Activa del Sistema</h4><h1 style="color:#0D47A1; margin:10px 0; font-size: 40px;">{st.session_state.get('tasa_bcv', 36.50):.2f} BS/$</h1></div>""", unsafe_allow_html=True)
        st.write("### 📝 Ajuste Manual")
        with st.form("registro_manual"):
            fecha_manual = st.date_input("Fecha a registrar/actualizar", datetime.today())
            tasa_manual = st.number_input("Valor de la Tasa (BS/$)", min_value=0.1, step=0.1, value=float(st.session_state.get('tasa_bcv', 36.50)))
            aplicar_ahora = st.checkbox("☑️ Aplicar esta tasa a la Caja ahora mismo", value=True)
            
            if st.form_submit_button("💾 Guardar / Actualizar Tasa", type="primary", use_container_width=True):
                fecha_str = fecha_manual.strftime("%d/%m/%Y")
                if fecha_str in df['Fecha'].values:
                    df.loc[df['Fecha'] == fecha_str, 'Tasa_Bs'] = tasa_manual
                    df.loc[df['Fecha'] == fecha_str, 'Hora'] = datetime.now().strftime("%I:%M %p")
                else:
                    nueva_tasa = {"Fecha": fecha_str, "Hora": datetime.now().strftime("%I:%M %p"), "Tasa_Bs": tasa_manual}
                    df = pd.concat([pd.DataFrame([nueva_tasa]), df], ignore_index=True)
                
                df.drop(columns=['Fecha_DT'], errors='ignore').to_csv(archivo_tasas, index=False)
                if aplicar_ahora: st.session_state.tasa_bcv = tasa_manual
                st.success("Guardado en disco permanentemente.")
                st.rerun()

    with col_der:
        opcion = st.radio("Ver registros por:", ["Todo el historial", "Última Semana", "Último Mes"], horizontal=True)
        hoy_dt = datetime.now()
        if opcion == "Última Semana": df_filtrado = df[df['Fecha_DT'] > (hoy_dt - timedelta(days=7))]
        elif opcion == "Último Mes": df_filtrado = df[df['Fecha_DT'] > (hoy_dt - timedelta(days=30))]
        else: df_filtrado = df

        tab1, tab2 = st.tabs(["📄 Tabla de Datos y PDF", "📈 Gráfico de Tendencia"])
        with tab1:
            df_display = df_filtrado.copy()
            df_display['Tasa_Bs_Str'] = df_display['Tasa_Bs'].map('{:,.2f} Bs'.format)
            st.dataframe(df_display[["Fecha", "Hora", "Tasa_Bs_Str"]], use_container_width=True, hide_index=True)
            if FPDF_DISPONIBLE and not df_filtrado.empty:
                st.download_button("📄 Exportar a PDF", data=generar_pdf_tasas(df_filtrado), file_name=f"Tasas.pdf", mime="application/pdf", use_container_width=True)
        with tab2:
            if len(df_filtrado) > 1: st.line_chart(df_filtrado.sort_values(by='Fecha_DT').set_index("Fecha")["Tasa_Bs"])
            else: st.info("Se necesitan 2 días de registro para el gráfico.")