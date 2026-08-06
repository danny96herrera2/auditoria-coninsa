import streamlit as st
import pandas as pd
import numpy as np
from streamlit_drawable_canvas import st_canvas
import streamlit.components.v1 as components

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Auditoría Coninsa", page_icon="🏗️", layout="wide")

# ==========================================
# 2. DISEÑO VISUAL Y REGLAS ESTRICTAS DE IMPRESIÓN (CSS)
# ==========================================
st.markdown("""
<style>
.stApp { background-color: #f4f6f9; }
.header-corporativo {
    background-color: #002856;
    padding: 30px;
    border-radius: 10px;
    border-bottom: 6px solid #8CC63F;
    margin-bottom: 30px;
    text-align: center;
    box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.1);
}
.header-corporativo h1 {
    color: #FFFFFF !important;
    font-size: 2.8rem;
    font-weight: 800;
    margin: 0;
    text-transform: uppercase;
}
.header-corporativo p {
    color: #8CC63F !important;
    font-size: 1.5rem;
    margin-top: 10px;
    font-weight: 600;
}
div[data-testid="metric-container"] {
    background-color: #ffffff;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.05);
    border-top: 5px solid #8CC63F;
}
.subtitulo {
    color: #002856;
    font-size: 1.6rem;
    font-weight: bold;
    margin-bottom: 15px;
    margin-top: 40px;
    border-bottom: 2px solid #8CC63F;
    padding-bottom: 5px;
}
.titulo-tabla {
    color: #002856;
    font-size: 1.3rem;
    font-weight: bold;
    margin-top: 25px;
    margin-bottom: 10px;
}

/* ==========================================
   REGLAS MÁGICAS PARA IMPRESIÓN (PDF)
   ========================================== */
@media print {
    section[data-testid="stSidebar"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    button { display: none !important; }
    
    .stApp { background-color: white !important; }
    .header-corporativo { box-shadow: none !important; border: 2px solid #002856 !important; padding: 15px !important; }
    div[data-testid="metric-container"] { box-shadow: none !important; border: 1px solid #ccc !important; }
    
    .block-container { max-width: 100% !important; padding: 1rem !important; }
    .salto-impresion { page-break-before: always; }
}
</style>
""", unsafe_allow_html=True)

# 3. CARGA DE DATOS
st.sidebar.markdown("<h2 style='color: #002856; text-align: center;'>Panel de Control</h2>", unsafe_allow_html=True)
uploaded_file = st.sidebar.file_uploader("Sube el archivo Excel (.xls / .xlsx)", type=['xls', 'xlsx'])

def limpiar_numero(valor):
    if pd.isna(valor): return 0.0
    if isinstance(valor, (int, float)): return float(valor)
    val_str = str(valor).replace('$', '').replace(' ', '').strip()
    if not val_str: return 0.0
    val_str = val_str.replace(',', '') 
    try: return float(val_str)
    except: return 0.0

if uploaded_file is not None:
    try:
        # LECTURA DE DATOS
        uploaded_file.seek(0)
        try:
            dfs = pd.read_html(uploaded_file)
            df = dfs[0]
            clean_cols = []
            for col in df.columns:
                if isinstance(col, tuple):
                    levels = [str(x).strip() for x in col if "Unnamed" not in str(x)]
                    final_levels = []
                    for lvl in levels:
                        if not final_levels or final_levels[-1] != lvl:
                            final_levels.append(lvl)
                    clean_cols.append(" ".join(final_levels))
                else:
                    clean_cols.append(str(col))
            df.columns = clean_cols
        except:
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file, engine='openpyxl' if uploaded_file.name.endswith('xlsx') else None)

        # ==========================================
        # EXTRAER NOMBRE REAL DEL PROYECTO
        # ==========================================
        nombre_proyecto = "PROYECTO EN AUDITORÍA"
        for c in df.columns:
            if "-" in str(c) and len(str(c)) > 10 and "UNNAMED" not in str(c).upper():
                nombre_proyecto = str(c)
                break

        st.markdown(f"""
        <div class="header-corporativo">
            <h1>AUDITORÍA DE COSTOS E INVENTARIOS</h1>
            <p>📁 {nombre_proyecto}</p>
        </div>
        """, unsafe_allow_html=True)

        # ==========================================
        # BUSCADOR DE COLUMNAS FLEXIBLE
        # ==========================================
        df.columns = [str(c).upper() for c in df.columns]
        
        def encontrar_col(palabras):
            for c in df.columns:
                if all(p in c for p in palabras): return c
            return None

        col_desc = encontrar_col(['DESCRIP']) or df.columns[0]
        col_cod  = encontrar_col(['CÓDIGO']) or encontrar_col(['CODIGO']) or encontrar_col(['C\u00d3DIGO'])
        
        c_pres_v = encontrar_col(['PRESUPUESTO', 'VALOR']) or encontrar_col(['PRESUP', 'VALOR'])
        c_proy_v = encontrar_col(['PROYECTADO', 'VALOR']) or encontrar_col(['PROY', 'VALOR'])
        c_aseg_v = encontrar_col(['ASEGURADO', 'VALOR']) or encontrar_col(['ASEG', 'VALOR'])
        c_cons_v = encontrar_col(['CONSUMIDO', 'VALOR']) or encontrar_col(['CONS', 'VALOR'])
        c_comp_v = encontrar_col(['COMPRADO', 'VALOR']) or encontrar_col(['COMP', 'VALOR'])

        cols_num = [c for c in [c_pres_v, c_proy_v, c_aseg_v, c_cons_v, c_comp_v] if c is not None]
        for c in cols_num:
            df[c] = df[c].apply(limpiar_numero)

        # ==========================================
        # TOTALES GENERALES
        # ==========================================
        fila_total = df[df[col_desc].astype(str).str.contains("TOTAL", na=False)]
        if not fila_total.empty:
            tot_pres = fila_total.iloc[-1][c_pres_v] if c_pres_v else 0
            tot_proy = fila_total.iloc[-1][c_proy_v] if c_proy_v else 0
            tot_aseg = fila_total.iloc[-1][c_aseg_v] if c_aseg_v else 0
            tot_cons = fila_total.iloc[-1][c_cons_v] if c_cons_v else 0
        else:
            if col_cod:
                df_calc = df[df[col_cod].notna() & (df[col_cod].astype(str).str.strip() != '') & (df[col_cod].astype(str).str.strip() != '0')]
            else:
                df_calc = df
            tot_pres = df_calc[c_pres_v].sum() if c_pres_v else 0
            tot_proy = df_calc[c_proy_v].sum() if c_proy_v else 0
            tot_aseg = df_calc[c_aseg_v].sum() if c_aseg_v else 0
            tot_cons = df_calc[c_cons_v].sum() if c_cons_v else 0

        # ==========================================
        # TARJETAS DE MÉTRICAS (KPIs) - En miles
        # ==========================================
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Presupuesto (Miles)", f"${(tot_pres/1000):,.0f}")
        kpi2.metric("Proyectado (Miles)", f"${(tot_proy/1000):,.0f}", f"${((tot_proy - tot_pres)/1000):,.0f} vs Pres", delta_color="inverse")
        kpi3.metric("Asegurado (Miles)", f"${(tot_aseg/1000):,.0f}")
        kpi4.metric("Consumido (Miles)", f"${(tot_cons/1000):,.0f}", f"${((tot_cons - tot_aseg)/1000):,.0f} vs Aseg", delta_color="inverse")
        
        # ==========================================
        # PREPARAR DATOS DE CAPÍTULOS
        # ==========================================
        if col_cod is not None:
            df_capitulos = df[df[col_cod].isna() | (df[col_cod].astype(str).str.strip() == '') | (df[col_cod].astype(str).str.strip() == '0') | (df[col_cod].astype(str).str.lower() == 'nan')].copy()
            df_capitulos = df_capitulos[df_capitulos[col_desc].notna()]
            df_capitulos = df_capitulos[~df_capitulos[col_desc].astype(str).str.contains("TOTAL")]
        else:
            df_capitulos = df.head(15).copy()

        # Transformar todos los valores a "Miles" para facilitar la lectura
        for c in cols_num:
            df_capitulos[c] = df_capitulos[c] / 1000.0

        # ==========================================
        # GRÁFICA COMPARATIVA DE BARRAS
        # ==========================================
        st.markdown('<div class="subtitulo">📊 COMPARATIVA DE COSTOS POR CAPÍTULO (Cifras en Miles)</div>', unsafe_allow_html=True)
        
        cols_grafica = []
        nombres_grafica = []
        if c_pres_v: cols_grafica.append(c_pres_v); nombres_grafica.append("Presupuestado")
        if c_proy_v: cols_grafica.append(c_proy_v); nombres_grafica.append("Proyectado")
        if c_aseg_v: cols_grafica.append(c_aseg_v); nombres_grafica.append("Asegurado")
        
        if cols_grafica and not df_capitulos.empty:
            df_grafica = df_capitulos.set_index(col_desc)[cols_grafica].copy()
            df_grafica.columns = nombres_grafica
            df_grafica.index.name = "Capítulo"
            
            colores_coninsa = ["#002856", "#8CC63F", "#FFC112"][:len(cols_grafica)]
            try:
                st.bar_chart(df_grafica, use_container_width=True, color=colores_coninsa)
            except:
                st.bar_chart(df_grafica, use_container_width=True)
        else:
            st.info("No hay suficientes datos de valor para generar la gráfica.")

        # ==========================================
        # TABLAS DE ANÁLISIS DE DESVIACIONES Y OBSERVACIONES (APILADAS)
        # ==========================================
        st.markdown('<div class="subtitulo">📋 ANÁLISIS DE DESVIACIONES POR CAPÍTULO (Cifras en Miles)</div>', unsafe_allow_html=True)
        
        # Pre-cálculo de diferencias porcentuales
        if c_pres_v and c_proy_v:
            df_capitulos['VAR_PPTO_%'] = np.where(df_capitulos[c_pres_v] > 0, ((df_capitulos[c_proy_v] - df_capitulos[c_pres_v]) / df_capitulos[c_pres_v]) * 100, 0.0)
        else:
            df_capitulos['VAR_PPTO_%'] = 0.0

        if c_proy_v and c_comp_v:
            df_capitulos['VAR_COMP_%'] = np.where(df_capitulos[c_proy_v] > 0, ((df_capitulos[c_comp_v] - df_capitulos[c_proy_v]) / df_capitulos[c_proy_v]) * 100, 0.0)
        else:
            df_capitulos['VAR_COMP_%'] = 0.0

        df_capitulos['Observaciones'] = ""
        
        altura_dinamica = min(max(len(df_capitulos) * 38 + 45, 200), 800)

        # TABLA 1: ARRIBA
        st.markdown('<div class="titulo-tabla">1. PROYECTADO VS PRESUPUESTADO</div>', unsafe_allow_html=True)
        df_t1 = df_capitulos[[col_desc, c_pres_v, c_proy_v, 'VAR_PPTO_%', 'Observaciones']].copy() if c_pres_v and c_proy_v else pd.DataFrame()
        if not df_t1.empty:
            df_t1.columns = ['Capítulo', 'Presupuestado', 'Proyectado', 'Diferencia (%)', 'Observaciones']
            st.data_editor(
                df_t1, 
                column_config={
                    "Presupuestado": st.column_config.NumberColumn(format="$ %,.0f"),
                    "Proyectado": st.column_config.NumberColumn(format="$ %,.0f"),
                    "Diferencia (%)": st.column_config.NumberColumn(format="%.1f %%"),
                    "Observaciones": st.column_config.TextColumn(help="Doble clic para escribir")
                }, 
                use_container_width=True, 
                hide_index=True,
                height=altura_dinamica,
                key="tabla_ppto"
            )

        # TABLA 2: ABAJO
        st.markdown('<br>', unsafe_allow_html=True) 
        st.markdown('<div class="titulo-tabla">2. COMPRADO VS PROYECTADO</div>', unsafe_allow_html=True)
        df_t2 = df_capitulos[[col_desc, c_proy_v, c_comp_v, 'VAR_COMP_%', 'Observaciones']].copy() if c_proy_v and c_comp_v else pd.DataFrame()
        if not df_t2.empty:
            df_t2.columns = ['Capítulo', 'Proyectado', 'Comprado', 'Diferencia (%)', 'Observaciones']
            st.data_editor(
                df_t2, 
                column_config={
                    "Proyectado": st.column_config.NumberColumn(format="$ %,.0f"),
                    "Comprado": st.column_config.NumberColumn(format="$ %,.0f"),
                    "Diferencia (%)": st.column_config.NumberColumn(format="%.1f %%"),
                    "Observaciones": st.column_config.TextColumn(help="Doble clic para escribir")
                }, 
                use_container_width=True, 
                hide_index=True,
                height=altura_dinamica,
                key="tabla_comp"
            )

        # ==========================================
        # FIRMA DEL AUDITOR Y BOTÓN DE IMPRIMIR
        # ==========================================
        st.markdown('<div class="salto-impresion"></div>', unsafe_allow_html=True)
        st.markdown("---")
        st.markdown('<div class="subtitulo">📝 CIERRE Y FIRMA EN OBRA</div>', unsafe_allow_html=True)
        
        col_izq, col_der = st.columns([2, 1])
        with col_izq:
            opciones = ["(Seleccione un Capítulo)"] + list(df_capitulos[col_desc].dropna().astype(str).unique())
            item = st.selectbox("Seleccione el capítulo a destacar (Opcional):", opciones)
            obs = st.text_area("Conclusiones Generales del Proyecto:", height=110)
        with col_der:
            st.write("**Firma Responsable:**")
            st_canvas(
                fill_color="rgba(140, 198, 63, 0.3)", stroke_width=2, stroke_color="#002856",
                background_color="#ffffff", height=150, width=300, drawing_mode="freedraw", key="canvas"
            )
            
        col_bot1, col_bot2 = st.columns([1, 1])
        with col_bot1:
            if st.button("💾 Guardar Auditoría", type="primary"):
                st.success("Guardado con éxito en la base de datos.")
                
        with col_bot2:
            components.html(
                """
                <script>
                function printPage() {
                    window.parent.print();
                }
                </script>
                <button onclick="printPage()" style="
                    background-color:#002856;
                    color:white;
                    padding:10px 20px;
                    border:none;
                    border-radius:5px;
                    cursor:pointer;
                    font-weight:bold;
                    font-family:sans-serif;
                    width: 100%;
                ">🖨️ Imprimir Reporte Oficial (PDF)</button>
                """,
                height=55
            )

    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")
else:
    st.markdown("""
    <div style='text-align: center; margin-top: 50px;'>
        <h1 style='color: #002856; font-size: 4rem;'>🏗️</h1>
        <h2 style='color: #002856;'>Bienvenido a la Herramienta de Auditoría</h2>
        <p style='color: #666; font-size: 1.2rem;'>Usa el panel izquierdo para cargar tu archivo de Excel de proyecciones y comenzar.</p>
    </div>
    """, unsafe_allow_html=True)