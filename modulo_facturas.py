import streamlit as st
import pandas as pd
import os

def ejecutar():
    st.markdown("""
        <style>
        .card-dinero {
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            color: white;
            font-weight: bold;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .monto-grande { font-size: 30px; margin-top: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.header("📄 Consolidado de Facturas y Pagos")
    if st.button("⬅️ VOLVER AL PANEL"):
        st.session_state.menu_principal = "Escritorio"; st.rerun()
    st.write("---")

    archivo = "data/ventas_realizadas.csv"
    if os.path.exists(archivo):
        df = pd.read_csv(archivo)
        
        # Filtro por turno actual para ver solo lo de hoy
        turno_actual = st.session_state.get('turno', 'Mañana')
        df_hoy = df[df['Turno'] == turno_actual]

        # Cálculos consolidados
        total_efectivo = df_hoy['Efectivo'].sum()
        total_movil = df_hoy['Pago_Movil'].sum()
        total_punto = df_hoy['Punto'].sum()
        total_general = df_hoy['Total_Bs'].sum()

        # --- CUADROS GRANDES DE DINERO ---
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.markdown(f'<div class="card-dinero" style="background-color:#28a745;">💵 EFECTIVO<div class="monto-grande">{total_efectivo:,.2f}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="card-dinero" style="background-color:#007bff;">📲 PAGO MÓVIL<div class="monto-grande">{total_movil:,.2f}</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="card-dinero" style="background-color:#6f42c1;">🏧 PUNTO<div class="monto-grande">{total_punto:,.2f}</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="card-dinero" style="background-color:#343a40;">💰 TOTAL VENDIDO<div class="monto-grande">{total_general:,.2f}</div></div>', unsafe_allow_html=True)

        st.write("### 📜 Detalle de Facturas del Turno")
        st.dataframe(df_hoy[["Hora", "Total_Bs", "Efectivo", "Pago_Movil", "Punto", "Productos"]], use_container_width=True, hide_index=True)

    else:
        st.info("Aún no hay ventas registradas en este turno.")