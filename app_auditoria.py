import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime, date
import altair as alt
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
/* REGLAS MÁGICAS PARA IMPRESIÓN (PDF) */
@media print {
    section[data-testid="stSidebar"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    button { display: none !important; }
    .stApp { background-color: white !important; }
    .header-corporativo { box-shadow: none !important; border: 2px solid #002856 !important; padding: 15px !important; }
    .block-container { max-width: 100% !important; padding: 1rem !important; }
    .stDataFrame, .stDataFrame > div { height: auto !important; max-height: none !important; overflow: visible !important; }
    .stTabs [data-baseweb="tab-panel"] { display: block !important; visibility: visible !important; height: auto !important; }
    .stTabs [role="tablist"] { display: none !important; } 
    .salto-impresion { page-break-before: always; }
}
</style>
""", unsafe_allow_html=True)

# 3. CARGA DE DATOS MULTI-ARCHIVO
st.sidebar.markdown("<h2 style='color: #002856; text-align: center;'>Panel de Control</h2>", unsafe_allow_html=True)
uploaded_file = st.sidebar.file_uploader("1. Archivo PRINCIPAL (.xls / .xlsx)", type=['xls', 'xlsx'])
st.sidebar.markdown("---")
uploaded_causas = st.sidebar.file_uploader("2. Archivo CAUSAS (Opcional)", type=['xls', 'xlsx'], help="Sube el archivo de Causas para sumar automáticamente el ajuste de BASE PPTO.")

def limpiar_numero(valor):
    if pd.isna(valor): return 0.0
    if isinstance(valor, (int, float)): return float(valor)
    val_str = str(valor).replace('$', '').replace(' ', '').strip()
    if not val_str: return 0.0
    val_str = val_str.replace(',', '') 
    try: return float(val_str)
    except: return 0.0

def extraer_ajuste_causas(file_causas):
    file_causas.seek(0)
    try:
        dfs = pd.read_html(file_causas)
        df_c = dfs[0]
    except:
        file_causas.seek(0)
        df_c = pd.read_excel(file_causas, engine='openpyxl' if file_causas.name.endswith('xlsx') else None)
        
    clean_cols_c = []
    for col in df_c.columns:
        if isinstance(col, tuple):
            levels = [str(x).strip() for x in col if "Unnamed" not in str(x)]
            final_levels = []
            for lvl in levels:
                if not final_levels or final_levels[-1] != lvl:
                    final_levels.append(lvl)
            clean_cols_c.append(" ".join(final_levels))
        else:
            clean_cols_c.append(str(col))
    df_c.columns = clean_cols_c

    meses_es = {'Enero': 1, 'Febrero': 2, 'Marzo': 3, 'Abril': 4, 'Mayo': 5, 'Junio': 6, 
                'Julio': 7, 'Agosto': 8, 'Septiembre': 9, 'Octubre': 10, 'Noviembre': 11, 'Diciembre': 12}
    date_cols = {}
    for col in df_c.columns:
        match = re.search(r'([A-Za-z]+)-(\d{2,4})', col)
        if match:
            mes_str = match.group(1).capitalize()
            year_str = match.group(2)
            if mes_str in meses_es:
                year = int(year_str)
                if year < 100: year += 2000
                date_cols[col] = datetime(year, meses_es[mes_str], 1)
                
    if not date_cols: return 0.0, "Sin fechas detectadas"
        
    hoy = datetime.now()
    most_recent_col = min(date_cols, key=lambda k: abs((date_cols[k] - hoy).days))
    
    col_desc_c = df_c.columns[0]
    base_row = df_c[df_c[col_desc_c].astype(str).str.upper().str.contains("BASE PPTO", na=False)]
    
    if not base_row.empty:
        val = base_row.iloc[-1][most_recent_col]
        try: return float(str(val).replace(',', '').replace('$', '').strip()), most_recent_col
        except: return 0.0, most_recent_col
    return 0.0, most_recent_col

if uploaded_file is not None:
    try:
        ajuste_ppto = 0.0
        info_col_causas = ""
        if uploaded_causas is not None:
            try:
                ajuste_ppto, info_col_causas = extraer_ajuste_causas(uploaded_causas)
            except Exception as e:
                st.sidebar.warning(f"Error leyendo Causas: {e}")

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

        df.columns = [str(c).upper() for c in df.columns]
        
        def encontrar_col(palabras):
            for c in df.columns:
                if all(p in c for p in palabras): return c
            return None

        col_desc = encontrar_col(['DESCRIP']) or df.columns[0]
        c_pres_v = encontrar_col(['PRESUPUESTO', 'VALOR']) or encontrar_col(['PRESUP', 'VALOR'])
        c_proy_v = encontrar_col(['PROYECTADO', 'VALOR']) or encontrar_col(['PROY', 'VALOR'])
        c_aseg_v = encontrar_col(['ASEGURADO', 'VALOR']) or encontrar_col(['ASEG', 'VALOR'])
        c_cons_v = encontrar_col(['CONSUMIDO', 'VALOR']) or encontrar_col(['CONS', 'VALOR'])

        cols_num = [c for c in [c_pres_v, c_proy_v, c_aseg_v, c_cons_v] if c is not None]
        for c in cols_num:
            df[c] = df[c].apply(limpiar_numero)

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

        # === APLICACIÓN DE AJUSTE Y CÁLCULOS ===
        tot_pres += ajuste_ppto
        por_consumir = tot_proy - tot_cons
        
        pct_cons = (tot_cons / tot_proy * 100) if tot_proy > 0 else 0
        pct_aseg = (tot_aseg / tot_proy * 100) if tot_proy > 0 else 0
        pct_por_consumir = (por_consumir / tot_proy * 100) if tot_proy > 0 else 0
        idx_proy = (tot_proy / tot_pres * 100) if tot_pres > 0 else 0

        # === RASTREADOR DE IMPREVISTOS Y REAJUSTES ===
        val_imprevistos = 0.0
        val_reajustes = 0.0
        
        if c_proy_v:
            for idx, row in df.iterrows():
                desc_val = str(row[col_desc]).strip().upper()
                if desc_val.startswith("39."):
                    if "IMPREVISTOS DE OBRA" in desc_val:
                        val_imprevistos = limpiar_numero(row[c_proy_v])
                    elif "REAJUSTE DE OBRA" in desc_val or "REAJUSTES DE OBRA" in desc_val:
                        val_reajustes = limpiar_numero(row[c_proy_v])

        # ESPACIO RESERVADO PARA EL BANNER
        banner_container = st.empty()

        # ==========================================
        # INTERFAZ DE PESTAÑAS (3 HOJAS)
        # ==========================================
        tab_capitulos, tab_items, tab_prog = st.tabs(["📑 Hoja 1: Resumen de Capítulos", "🗂️ Hoja 2: Detalle por Ítems", "🗓️ Hoja 3: Programación"])

        with tab_prog:
            st.markdown('<div class="subtitulo">🗓️ % Programa Vs % Consumido</div>', unsafe_allow_html=True)
            st.info("Digita las fechas y los porcentajes. El sistema calculará los meses automáticamente y los enviará al banner superior.")
            
            # Fila 1: Fechas (Inputs)
            c1, c2, c3 = st.columns(3)
            val_f_inicio = c1.date_input("Fecha inicio", value=None)
            val_f_fin = c2.date_input("Fecha fin", value=None)
            val_f_auditoria = c3.date_input("Fecha de auditoría", value=datetime.today())

            # Cálculos automáticos de tiempos
            meses_tot = 0.0
            meses_ejec = 0.0
            meses_falt = 0.0
            
            if val_f_inicio and val_f_fin:
                meses_tot = (val_f_fin - val_f_inicio).days / 30.0
            if val_f_inicio and val_f_auditoria:
                meses_ejec = (val_f_auditoria - val_f_inicio).days / 30.0
                
            meses_falt = meses_tot - meses_ejec

            st.markdown(f"""
            <div style="background-color: #E2EFD9; padding: 15px; border-radius: 5px; text-align: center; color: black; font-weight: bold; margin-bottom: 20px;">
                Meses de ejecución total: <span style="color: #257A72; font-size: 1.2rem;">{meses_tot:.1f}</span> &nbsp; | &nbsp; 
                Meses ejecutados: <span style="color: #257A72; font-size: 1.2rem;">{meses_ejec:.1f}</span> &nbsp; | &nbsp; 
                Meses por ejecutar: <span style="color: #257A72; font-size: 1.2rem;">{meses_falt:.1f}</span>
            </div>
            """, unsafe_allow_html=True)

            # Fila 2: Porcentajes y Atraso (Inputs)
            c4, c5, c6 = st.columns(3)
            val_av_real = c4.number_input("% avance real", value=0.0, step=0.1, format="%.1f")
            val_av_prog = c5.number_input("% avance programado", value=0.0, step=0.1, format="%.1f")
            val_dias_atr = c6.number_input("Días de atraso", value=0, step=1)

        # ==========================================
        # CONSTRUCCIÓN DEL BANNER HTML (SE INYECTA ARRIBA)
        # ==========================================
        html_banner = f"""
        <div style="display: flex; width: 100%; gap: 15px; font-family: sans-serif; margin-bottom: 25px;">
            
            <!-- BLOQUE 1: VERDE OLIVO -->
            <div style="display: flex; flex: 2.8; background-color: #9DBB61; padding: 15px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">
                <div style="flex: 1; text-align: center; border-right: 1px solid rgba(255,255,255,0.4); padding-right: 5px; display: flex; flex-direction: column; justify-content: center;">
                    <div style="color: black; font-weight: 800; font-size: 1rem; line-height: 1.2;">Vr. PPTO<br>+Adicionales</div>
                    <div style="color: white; font-weight: bold; font-size: 1.4rem; margin-top: 5px;">$ {tot_pres:,.0f}</div>
                </div>
                <div style="flex: 1; text-align: center; padding-left: 5px; display: flex; flex-direction: column; justify-content: center;">
                    <div style="color: black; font-weight: 800; font-size: 1rem; line-height: 1.2;"><br>Vr. Proyección</div>
                    <div style="color: white; font-weight: bold; font-size: 1.4rem; margin-top: 5px;">$ {tot_proy:,.0f}</div>
                </div>
                <div style="flex: 0.4; display: flex; align-items: center; justify-content: center; border-left: 4px solid white; margin-left: 15px; padding-left: 10px;">
                    <span style="color: black; font-weight: 900; font-size: 1.3rem;">{idx_proy:,.0f}%</span>
                </div>
            </div>
            
            <!-- BLOQUE 2: BEIGE / VERDE CLARO -->
            <div style="display: flex; flex-direction: column; flex: 4.2; gap: 8px;">
                <div style="display: flex; gap: 8px; flex: 1;">
                    <div style="flex: 1; background-color: #E2EFD9; padding: 10px; border-radius: 5px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="color: black; font-weight: 800; font-size: 0.95rem;">Vr. Consumido</div>
                            <div style="font-size: 1.1rem; color: #333; font-weight: bold; margin-top: 3px;">$ {tot_cons:,.0f}</div>
                        </div>
                        <div style="font-size: 1.2rem; color: #555; font-weight: bold;">{pct_cons:.0f}%</div>
                    </div>
                    <div style="flex: 1; background-color: #E2EFD9; padding: 10px; border-radius: 5px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="color: black; font-weight: 800; font-size: 0.95rem;">Vr. Asegurado</div>
                            <div style="font-size: 1.1rem; color: #333; font-weight: bold; margin-top: 3px;">$ {tot_aseg:,.0f}</div>
                        </div>
                        <div style="font-size: 1.2rem; color: #555; font-weight: bold;">{pct_aseg:.0f}%</div>
                    </div>
                </div>
                <div style="display: flex; gap: 8px; flex: 1;">
                    <div style="flex: 1.2; background-color: #E2EFD9; padding: 10px; border-radius: 5px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="color: black; font-weight: 800; font-size: 0.95rem;">Vr. Por consumir</div>
                            <div style="font-size: 1.1rem; color: #333; font-weight: bold; margin-top: 3px;">$ {por_consumir:,.0f}</div>
                        </div>
                        <div style="font-size: 1.2rem; color: #555; font-weight: bold;">{pct_por_consumir:.0f}%</div>
                    </div>
                    <div style="flex: 0.9; background-color: #E2EFD9; padding: 10px; border-radius: 5px; display: flex; flex-direction: column; justify-content: center;">
                        <div style="color: black; font-weight: 800; font-size: 0.9rem; text-align: center;">Imprevistos</div>
                        <div style="color: #333; font-weight: bold; text-align: center; margin-top: 3px;">$ {val_imprevistos:,.0f}</div>
                    </div>
                    <div style="flex: 0.9; background-color: #E2EFD9; padding: 10px; border-radius: 5px; display: flex; flex-direction: column; justify-content: center;">
                        <div style="color: black; font-weight: 800; font-size: 0.9rem; text-align: center;">Reajustes</div>
                        <div style="color: #333; font-weight: bold; text-align: center; margin-top: 3px;">$ {val_reajustes:,.0f}</div>
                    </div>
                </div>
            </div>
            
            <!-- BLOQUE 3: VERDE OSCURO (TEAL) -->
            <div style="display: flex; flex-direction: column; flex: 3; gap: 8px;">
                <div style="display: flex; gap: 8px; flex: 1;">
                    <div style="flex: 1; background-color: #257A72; color: white; padding: 10px; border-radius: 5px; display: flex; flex-direction: column; justify-content: center; text-align: center;">
                        <div style="font-weight: 800; color: black; font-size: 0.85rem;">% avance real</div>
                        <div style="font-size: 1.2rem; font-weight: bold; margin-top: 3px;">{val_av_real}%</div>
                    </div>
                    <div style="flex: 1; background-color: #257A72; color: white; padding: 10px; border-radius: 5px; display: flex; flex-direction: column; justify-content: center; text-align: center;">
                        <div style="font-weight: 800; color: black; font-size: 0.85rem;">Días de atraso</div>
                        <div style="font-size: 1.2rem; font-weight: bold; margin-top: 3px;">{val_dias_atr}</div>
                    </div>
                </div>
                <div style="display: flex; gap: 8px; flex: 1;">
                    <div style="flex: 1; background-color: #257A72; color: white; padding: 10px; border-radius: 5px; display: flex; flex-direction: column; justify-content: center; text-align: center;">
                        <div style="font-weight: 800; color: black; font-size: 0.85rem;">% avance programado</div>
                        <div style="font-size: 1.2rem; font-weight: bold; margin-top: 3px;">{val_av_prog}%</div>
                    </div>
                    <div style="flex: 1; background-color: #257A72; color: white; padding: 10px; border-radius: 5px; display: flex; flex-direction: column; justify-content: center; text-align: center;">
                        <div style="font-weight: 800; color: black; font-size: 0.85rem;">Meses faltantes</div>
                        <div style="font-size: 1.2rem; font-weight: bold; margin-top: 3px;">{meses_falt:.1f}</div>
                    </div>
                </div>
            </div>
            
        </div>
        """
        # Inyectar el banner en el espacio reservado arriba
        banner_container.markdown(html_banner, unsafe_allow_html=True)


        # ==========================================
        # FUNCIONES DE TABLAS Y GRÁFICAS (HOJA 1 Y 2)
        # ==========================================
        patron_capitulos = r'^\s*\d{1,2}\s*[-]'
        es_capitulo = df[col_desc].astype(str).str.contains(patron_capitulos, regex=True, na=False)
        es_total = df[col_desc].astype(str).str.upper().str.contains("TOTAL", na=False)
        
        df_capitulos = df[es_capitulo & ~es_total].copy()
        if df_capitulos.empty:
            patron_capitulos_flexible = r'^\s*\d{1,2}\s+[A-Za-z]'
            es_capitulo = df[col_desc].astype(str).str.contains(patron_capitulos_flexible, regex=True, na=False)
            df_capitulos = df[es_capitulo & ~es_total].copy()

        df_items = df[(~es_capitulo) & (~es_total) & (df[col_desc].str.strip() != "")].copy()
        if c_pres_v and c_proy_v:
            df_items = df_items[(df_items[c_pres_v] > 0) | (df_items[c_proy_v] > 0)]

        for c in cols_num:
            if not df_capitulos.empty: df_capitulos[c] = df_capitulos[c] / 1000.0
            if not df_items.empty: df_items[c] = df_items[c] / 1000.0

        def generar_tablas(df_datos, key_prefix):
            if c_pres_v and c_proy_v:
                df_datos['VAR_PPTO_%'] = np.where(df_datos[c_pres_v] > 0, ((df_datos[c_proy_v] - df_datos[c_pres_v]) / df_datos[c_pres_v]) * 100, 0.0)
            else: df_datos['VAR_PPTO_%'] = 0.0

            if c_proy_v and c_aseg_v:
                df_datos['VAR_ASEG_%'] = np.where(df_datos[c_proy_v] > 0, ((df_datos[c_aseg_v] - df_datos[c_proy_v]) / df_datos[c_proy_v]) * 100, 0.0)
            else: df_datos['VAR_ASEG_%'] = 0.0

            df_datos['Observaciones'] = ""
            altura_dinamica = max((len(df_datos) * 38) + 45, 150) 

            st.markdown('<div class="titulo-tabla">1. PROYECTADO VS PRESUPUESTADO</div>', unsafe_allow_html=True)
            df_t1 = df_datos[[col_desc, c_pres_v, c_proy_v, 'VAR_PPTO_%', 'Observaciones']].copy() if c_pres_v and c_proy_v else pd.DataFrame()
            if not df_t1.empty:
                df_t1.columns = ['Descripción', 'Presupuestado', 'Proyectado', 'Diferencia (%)', 'Observaciones']
                st.data_editor(df_t1, column_config={"Presupuestado": st.column_config.NumberColumn(format="$ %,.0f"), "Proyectado": st.column_config.NumberColumn(format="$ %,.0f"), "Diferencia (%)": st.column_config.NumberColumn(format="%.1f %%"), "Observaciones": st.column_config.TextColumn()}, use_container_width=True, hide_index=True, height=altura_dinamica, key=f"{key_prefix}_1")

            st.markdown('<br>', unsafe_allow_html=True) 
            st.markdown('<div class="titulo-tabla">2. ASEGURADO VS PROYECTADO</div>', unsafe_allow_html=True)
            df_t2 = df_datos[[col_desc, c_proy_v, c_aseg_v, 'VAR_ASEG_%', 'Observaciones']].copy() if c_proy_v and c_aseg_v else pd.DataFrame()
            if not df_t2.empty:
                df_t2.columns = ['Descripción', 'Proyectado', 'Asegurado', 'Diferencia (%)', 'Observaciones']
                st.data_editor(df_t2, column_config={"Proyectado": st.column_config.NumberColumn(format="$ %,.0f"), "Asegurado": st.column_config.NumberColumn(format="$ %,.0f"), "Diferencia (%)": st.column_config.NumberColumn(format="%.1f %%"), "Observaciones": st.column_config.TextColumn()}, use_container_width=True, hide_index=True, height=altura_dinamica, key=f"{key_prefix}_2")

        with tab_capitulos:
            st.markdown('<div class="subtitulo">📊 COMPARATIVA GERENCIAL (Capítulos)</div>', unsafe_allow_html=True)
            todos_los_capitulos = df_capitulos[col_desc].dropna().unique().tolist() if not df_capitulos.empty else []
            modo_filtro = st.radio("Configuración de Visualización:", ["Mostrar Todos los Capítulos", "Seleccionar Manualmente"], horizontal=True)
            
            if modo_filtro == "Mostrar Todos los Capítulos":
                capitulos_seleccionados = todos_los_capitulos
            else:
                capitulos_seleccionados = st.multiselect("🔍 Selecciona los Capítulos que deseas analizar:", options=todos_los_capitulos, default=[])

            cols_grafica = []
            nombres_grafica = []
            if c_pres_v: cols_grafica.append(c_pres_v); nombres_grafica.append("Presupuestado")
            if c_proy_v: cols_grafica.append(c_proy_v); nombres_grafica.append("Proyectado")
            if c_aseg_v: cols_grafica.append(c_aseg_v); nombres_grafica.append("Asegurado")
            
            if cols_grafica and not df_capitulos.empty and capitulos_seleccionados:
                df_grafica = df_capitulos.set_index(col_desc)[cols_grafica].copy()
                df_grafica.columns = nombres_grafica
                df_grafica.index.name = "Capítulo" 
                
                df_grafica_filtrada = df_grafica[df_grafica.index.isin(capitulos_seleccionados)].reset_index()
                df_fin_melt = df_grafica_filtrada.melt(id_vars="Capítulo", var_name="Métrica", value_name="Valor")
                colores_coninsa = ["#002856", "#8CC63F", "#FFC112"][:len(cols_grafica)]
                
                st.markdown("**Cifras Financieras (En Miles)**")
                chart_fin = alt.Chart(df_fin_melt).mark_bar().encode(
                    x=alt.X('Capítulo:N', title="", axis=alt.Axis(labelAngle=-45)),
                    xOffset='Métrica:N', 
                    y=alt.Y('Valor:Q', title="Valor ($ Miles)", axis=alt.Axis(format="$,.0f")),
                    color=alt.Color('Métrica:N', scale=alt.Scale(domain=nombres_grafica, range=colores_coninsa), legend=alt.Legend(title="Métrica", orient="top")),
                    tooltip=['Capítulo', 'Métrica', alt.Tooltip('Valor:Q', title='Miles', format="$,.0f")]
                )
                st.altair_chart(chart_fin, use_container_width=True)

            cols_porcentajes = []
            nombres_pct = []
            if c_proy_v and c_aseg_v:
                df_capitulos['% Aseg vs Proy'] = np.where(df_capitulos[c_proy_v] > 0, df_capitulos[c_aseg_v] / df_capitulos[c_proy_v], 0.0)
                cols_porcentajes.append('% Aseg vs Proy')
                nombres_pct.append("Asegurado / Proyectado")
                
            if c_cons_v and c_proy_v:
                df_capitulos['% Cons vs Proy'] = np.where(df_capitulos[c_proy_v] > 0, df_capitulos[c_cons_v] / df_capitulos[c_proy_v], 0.0)
                cols_porcentajes.append('% Cons vs Proy')
                nombres_pct.append("Consumido / Proyectado")
                
            if cols_porcentajes and not df_capitulos.empty and capitulos_seleccionados:
                df_grafica_pct = df_capitulos.set_index(col_desc)[cols_porcentajes].copy()
                df_grafica_pct.columns = nombres_pct
                df_grafica_pct.index.name = "Capítulo"
                
                df_grafica_pct_filtrada = df_grafica_pct[df_grafica_pct.index.isin(capitulos_seleccionados)].reset_index()
                df_pct_melt = df_grafica_pct_filtrada.melt(id_vars="Capítulo", var_name="Métrica", value_name="Porcentaje")
                df_pct_melt['Posicion_Texto'] = df_pct_melt['Porcentaje'] / 2
                
                colores_pct = ["#E74C3C", "#3498DB"][:len(cols_porcentajes)]
                
                st.markdown("**Índices de Ejecución (%)**")
                base_pct = alt.Chart(df_pct_melt).encode(
                    x=alt.X('Capítulo:N', title="", axis=alt.Axis(labelAngle=-45)),
                    xOffset='Métrica:N', 
                    color=alt.Color('Métrica:N', scale=alt.Scale(domain=nombres_pct, range=colores_pct), legend=alt.Legend(title="Indicador", orient="top")),
                    tooltip=['Capítulo', 'Métrica', alt.Tooltip('Porcentaje:Q', format=".1%")]
                )
                bar_pct = base_pct.mark_bar().encode(y=alt.Y('Porcentaje:Q', title="Porcentaje (%)", axis=alt.Axis(format=".0%")))
                text_pct = base_pct.mark_text(align='center', baseline='middle', color='white', fontWeight='bold', fontSize=11).encode(
                    y=alt.Y('Posicion_Texto:Q'), text=alt.Text('Porcentaje:Q', format=".1%")
                )
                chart_pct = (bar_pct + text_pct).configure_view(strokeWidth=0)
                st.altair_chart(chart_pct, use_container_width=True)
                
            elif not capitulos_seleccionados:
                st.info("👈 Selecciona al menos un capítulo en el filtro para ver las gráficas.")
            
            st.markdown('<div class="subtitulo">📋 TABLAS DE CONTROL - Nivel Capítulo</div>', unsafe_allow_html=True)
            generar_tablas(df_capitulos, "capitulos")

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
            st_canvas(fill_color="rgba(140, 198, 63, 0.3)", stroke_width=2, stroke_color="#002856", background_color="#ffffff", height=150, width=300, drawing_mode="freedraw", key="canvas")
            
        col_bot1, col_bot2 = st.columns([1, 1])
        with col_bot1:
            if st.button("💾 Guardar Auditoría", type="primary"):
                st.success(f"Auditoría cerrada con éxito por {nombre_auditor if nombre_auditor else 'el auditor'}.")
                
        with col_bot2:
            components.html(
                """
                <script>
                function printPage() {
                    try { window.parent.print(); } 
                    catch (e) {
                        try { window.top.print(); } 
                        catch (e2) { window.print(); }
                    }
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
                ">🖨️ Imprimir Reporte (o presiona Ctrl+P)</button>
                """, height=55
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
