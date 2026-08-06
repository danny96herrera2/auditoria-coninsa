import streamlit as st
import pandas as pd
import numpy as np
import re
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
    
    /* Forzar que las tablas se expandan al 100% sin scroll al imprimir */
    .stDataFrame, .stDataFrame > div { height: auto !important; max-height: none !important; overflow: visible !important; }
    
    /* MAGIA: Forzar que todas las pestañas (tabs) se impriman una debajo de la otra */
    .stTabs [data-baseweb="tab-panel"] { display: block !important; visibility: visible !important; }
    .stTabs [role="tablist"] { display: none !important; } /* Oculta los botones de las pestañas en el papel */
    
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

        # NOMBRE DEL PROYECTO
        nombre_proyecto = "PROYECTO EN AUDITORÍA"
        for c in df.columns:
            if "-" in str(c) and len(str(c)) > 10 and "UNNAMED" not in str(c).upper():
                nombre_proyecto = str(c)
                break

        st.markdown(f"""
        <div class="header-corporativo">
            <h1>AUDITORÍA DE COSTOS</h1>
            <p>📁 {nombre_proyecto}</p>
        </div>
        """, unsafe_allow_html=True)

        # COLUMNAS FLEXIBLES
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

        # TOTALES GENERALES
        df[col_desc] = df[col_desc].fillna("")
        fila_total = df[df[col_desc].astype(str).str.upper().str.contains("TOTAL", na=False)]
        
        if not fila_total.empty:
            tot_pres = fila_total.iloc[-1][c_pres_v] if c_pres_v else 0
            tot_proy = fila_total.iloc[-1][c_proy_v] if c_proy_v else 0
            tot_aseg = fila_total.iloc[-1][c_aseg_v] if c_aseg_v else 0
            tot_cons = fila_total.iloc[-1][c_cons_v] if c_cons_v else 0
        else:
            tot_pres = df[c_pres_v].sum() if c_pres_v else 0
            tot_proy = df[c_proy_v].sum() if c_proy_v else 0
            tot_aseg = df[c_aseg_v].sum() if c_aseg_v else 0
            tot_cons = df[c_cons_v].sum() if c_cons_v else 0

        # TARJETAS DE MÉTRICAS (En miles)
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Presupuesto (Miles)", f"${(tot_pres/1000):,.0f}")
        kpi2.metric("Proyectado (Miles)", f"${(tot_proy/1000):,.0f}", f"${((tot_proy - tot_pres)/1000):,.0f} vs Pres", delta_color="inverse")
        kpi3.metric("Asegurado (Miles)", f"${(tot_aseg/1000):,.0f}")
        kpi4.metric("Consumido (Miles)", f"${(tot_cons/1000):,.0f}", f"${((tot_cons - tot_aseg)/1000):,.0f} vs Aseg", delta_color="inverse")
        
        # ==========================================
        # FILTRO INTELIGENTE: CAPÍTULOS VS ÍTEMS
        # ==========================================
        # Regla: Capítulos inician con 1 o 2 números seguidos de un guion (ej. "1-PRELIMINARES") o espacio
        patron_capitulos = r'^\s*\d{1,2}\s*[-]'
        es_capitulo = df[col_desc].astype(str).str.contains(patron_capitulos, regex=True, na=False)
        es_total = df[col_desc].astype(str).str.upper().str.contains("TOTAL", na=False)
        
        df_capitulos = df[es_capitulo & ~es_total].copy()
        
        # Si la regla del guion no encuentra nada, flexibilizamos a que solo inicie con número y texto
        if df_capitulos.empty:
            patron_capitulos_flexible = r'^\s*\d{1,2}\s+[A-Za-z]'
            es_capitulo = df[col_desc].astype(str).str.contains(patron_capitulos_flexible, regex=True, na=False)
            df_capitulos = df[es_capitulo & ~es_total].copy()

        # Los ítems son todas las filas numéricas que NO son capítulos ni totales
        df_items = df[(~es_capitulo) & (~es_total) & (df[col_desc].str.strip() != "")].copy()
        # Filtramos ítems vacíos donde todo es cero
        if c_pres_v and c_proy_v:
            df_items = df_items[(df_items[c_pres_v] > 0) | (df_items[c_proy_v] > 0)]

        # Transformar a Miles
        for c in cols_num:
            if not df_capitulos.empty: df_capitulos[c] = df_capitulos[c] / 1000.0
            if not df_items.empty: df_items[c] = df_items[c] / 1000.0

        # ==========================================
        # FUNCIÓN PARA CREAR TABLAS (Reutilizable)
        # ==========================================
        def generar_tablas(df_datos, key_prefix):
            if c_pres_v and c_proy_v:
                df_datos['VAR_PPTO_%'] = np.where(df_datos[c_pres_v] > 0, ((df_datos[c_proy_v] - df_datos[c_pres_v]) / df_datos[c_pres_v]) * 100, 0.0)
            else: df_datos['VAR_PPTO_%'] = 0.0

            if c_proy_v and c_aseg_v:
                df_datos['VAR_ASEG_%'] = np.where(df_datos[c_proy_v] > 0, ((df_datos[c_aseg_v] - df_datos[c_proy_v]) / df_datos[c_proy_v]) * 100, 0.0)
            else: df_datos['VAR_ASEG_%'] = 0.0

            df_datos['Observaciones'] = ""
            altura_dinamica = min(max((len(df_datos) * 36) + 40, 200), 800) # Límite en pantalla (se expande al imprimir)

            st.markdown('<div class="titulo-tabla">1. PROYECTADO VS PRESUPUESTADO</div>', unsafe_allow_html=True)
            df_t1 = df_datos[[col_desc, c_pres_v, c_proy_v, 'VAR_PPTO_%', 'Observaciones']].copy() if c_pres_v and c_proy_v else pd.DataFrame()
            if not df_t1.empty:
                df_t1.columns = ['Descripción', 'Presupuestado', 'Proyectado', 'Diferencia (%)', 'Observaciones']
                st.data_editor(
                    df_t1, 
                    column_config={
                        "Presupuestado": st.column_config.NumberColumn(format="$ %,.0f"),
                        "Proyectado": st.column_config.NumberColumn(format="$ %,.0f"),
                        "Diferencia (%)": st.column_config.NumberColumn(format="%.1f %%"),
                        "Observaciones": st.column_config.TextColumn(help="Doble clic para escribir")
                    }, 
                    use_container_width=True, hide_index=True, height=altura_dinamica, key=f"{key_prefix}_1"
                )

            st.markdown('<br>', unsafe_allow_html=True) 
            st.markdown('<div class="titulo-tabla">2. ASEGURADO VS PROYECTADO</div>', unsafe_allow_html=True)
            df_t2 = df_datos[[col_desc, c_proy_v, c_aseg_v, 'VAR_ASEG_%', 'Observaciones']].copy() if c_proy_v and c_aseg_v else pd.DataFrame()
            if not df_t2.empty:
                df_t2.columns = ['Descripción', 'Proyectado', 'Asegurado', 'Diferencia (%)', 'Observaciones']
                st.data_editor(
                    df_t2, 
                    column_config={
                        "Proyectado": st.column_config.NumberColumn(format="$ %,.0f"),
                        "Asegurado": st.column_config.NumberColumn(format="$ %,.0f"),
                        "Diferencia (%)": st.column_config.NumberColumn(format="%.1f %%"),
                        "Observaciones": st.column_config.TextColumn(help="Doble clic para escribir")
                    }, 
                    use_container_width=True, hide_index=True, height=altura_dinamica, key=f"{key_prefix}_2"
                )

        # ==========================================
        # INTERFAZ DE PESTAÑAS (HOJAS)
        # ==========================================
        tab_capitulos, tab_items = st.tabs(["📑 Hoja 1: Resumen de Capítulos", "🗂️ Hoja 2: Detalle por Ítems"])

        # ---> HOJA 1: CAPÍTULOS
        with tab_capitulos:
            st.markdown('<div class="subtitulo">📊 COMPARATIVA GERENCIAL (Capítulos)</div>', unsafe_allow_html=True)
            
            # FILTRO PARA GRÁFICA
            todos_los_capitulos = df_capitulos[col_desc].dropna().unique().tolist() if not df_capitulos.empty else []
            capitulos_seleccionados = st.multiselect(
                "🔍 Filtra los Capítulos de la gráfica:", 
                options=todos_los_capitulos, default=todos_los_capitulos
            )

            cols_grafica = []
            nombres_grafica = []
            if c_pres_v: cols_grafica.append(c_pres_v); nombres_grafica.append("Presupuestado")
            if c_proy_v: cols_grafica.append(c_proy_v); nombres_grafica.append("Proyectado")
            if c_aseg_v: cols_grafica.append(c_aseg_v); nombres_grafica.append("Asegurado")
            
            if cols_grafica and not df_capitulos.empty:
                df_grafica = df_capitulos.set_index(col_desc)[cols_grafica].copy()
                df_grafica.columns = nombres_grafica
                df_grafica_filtrada = df_grafica[df_grafica.index.isin(capitulos_seleccionados)]
                
                colores_coninsa = ["#002856", "#8CC63F", "#FFC112"][:len(cols_grafica)]
                try: st.bar_chart(df_grafica_filtrada, use_container_width=True, color=colores_coninsa)
                except: st.bar_chart(df_grafica_filtrada, use_container_width=True)
            
            st.markdown('<div class="subtitulo">📋 TABLAS DE CONTROL - Nivel Capítulo</div>', unsafe_allow_html=True)
            generar_tablas(df_capitulos, "capitulos")

        # ---> HOJA 2: ÍTEMS
        with tab_items:
            st.markdown('<div class="subtitulo">🔍 DESGLOSE DETALLADO - Nivel Ítem</div>', unsafe_allow_html=True)
            if df_items.empty:
                st.info("No se detectaron ítems desglosados en el archivo Excel.")
            else:
                generar_tablas(df_items, "items")

        # ==========================================
        # FIRMA DEL AUDITOR Y BOTÓN DE IMPRIMIR
        # ==========================================
        st.markdown('<div class="salto-impresion"></div>', unsafe_allow_html=True)
        st.markdown("---")
        st.markdown('<div class="subtitulo">📝 CIERRE Y FIRMA EN OBRA</div>', unsafe_allow_html=True)
        
        col_izq, col_der = st.columns([2, 1])
        with col_izq:
            obs = st.text_area("Conclusiones Generales de la Auditoría:", height=110)
        with col_der:
            nombre_auditor = st.text_input("👤 Nombre del Auditor Responsable:")
            st.write("**Firma:**")
            st_canvas(
                fill_color="rgba(140, 198, 63, 0.3)", stroke_width=2, stroke_color="#002856",
                background_color="#ffffff", height=150, width=300, drawing_mode="freedraw", key="canvas"
            )
            
        col_bot1, col_bot2 = st.columns([1, 1])
        with col_bot1:
            if st.button("💾 Guardar Auditoría", type="primary"):
                st.success(f"Auditoría cerrada con éxito por {nombre_auditor if nombre_auditor else 'el auditor'}.")
                
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
                ">🖨️ Imprimir Reporte (Incluye ambas hojas)</button>
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
