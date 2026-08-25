import dash
from dash import dcc, html, Input, Output, State, dash_table
from dash.dash_table.Format import Format, Scheme, Symbol, Group
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import os
import unicodedata
import plotly.graph_objects as go
import plotly.express as px
import textwrap
import gc  

# --- LIBRERÍAS GITHUB ---
from github import Github

# Reducimos drásticamente los elementos visuales precargados para ahorrar RAM
pd.set_option("styler.render.max_elements", 10000) 

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LITERA], suppress_callback_exceptions=True)
app.title = "Dashboard Coninsa PRO"
server = app.server

# =====================================================================
# 🖨️ CONFIGURACIÓN DE PLANTILLA HTML
# =====================================================================
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            .hoja-papel { background: white; box-shadow: 0 4px 12px rgba(0,0,0,0.15); padding: 50px; margin: 20px auto; max-width: 1000px; border-radius: 5px; }
            @media print {
                body * { visibility: hidden; } 
                #zona-impresion, #zona-impresion * { visibility: visible; } 
                #zona-impresion { position: absolute; left: 0; top: 0; width: 100%; margin: 0; padding: 0; box-shadow: none; }
                #btn_imprimir { display: none !important; } 
                .hoja-papel { padding: 0; margin: 0; max-width: 100%; box-shadow: none; border: none; }
                .dash-table-container .dash-spreadsheet-container { max-height: none !important; height: auto !important; }
                .salto-pagina { page-break-before: always; }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>{%config%}{%scripts%}{%renderer%}</footer>
    </body>
</html>
'''

# =====================================================================
# 🔐 CONFIGURACIÓN DE APIS Y GITHUB (Usando Variables de Entorno)
# =====================================================================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = "danny96herrera2/dashboard-coninsa"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

C_AZUL = '#223983'
C_VERDE = '#00A54C'
C_TEAL = '#006e69'
C_LIME = '#7FC242'
C_GRIS = '#CBCCCB'
C_GRIS_BG = '#F8FAFC'
C_TEXTO = '#334155'
C_ROJO_ICOCED = '#cb0000' 
C_AMARILLO_REA = '#FFC112'

def guardar_en_github(df, nombre_archivo, mensaje_commit):
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        contenido_csv = df.to_csv(sep=';', index=False, encoding='utf-8-sig')
        try:
            contents = repo.get_contents(nombre_archivo)
            repo.update_file(contents.path, mensaje_commit, contenido_csv, contents.sha)
        except:
            repo.create_file(nombre_archivo, mensaje_commit, contenido_csv)
        return "Éxito"
    except Exception as e:
        return f"Error de GitHub: {str(e)}"

def limpiar_texto(texto):
    if pd.isna(texto): return ""
    return ''.join(c for c in unicodedata.normalize('NFD', str(texto).strip().upper()) if unicodedata.category(c) != 'Mn')

def leer_csv_robusto(ruta):
    if not os.path.exists(ruta): return pd.DataFrame()
    for enc in ['utf-8-sig', 'utf-8', 'latin1', 'cp1252']:
        try: return pd.read_csv(ruta, sep=';', encoding=enc)
        except UnicodeDecodeError: continue
    return pd.DataFrame()

# OPTIMIZACIÓN: Reducción extrema de tipos de datos para RAM
def optimizar_memoria(df):
    if df.empty: return df
    for col in df.select_dtypes(include=['float64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='float')
    for col in df.columns:
        if col in ['Ciudad', 'Categoria', 'Nombre_Insumo', 'Fuente']:
            df[col] = df[col].astype('category')
    return df

df_m, df_j, df_city, df_nac, df_ext, df_h_cat = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
df_camacol, df_icoced, df_ipc, df_reajuste = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
df_b100_ins, df_b100_cat, df_b100_city, df_b100_nac = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
fechas_disp, zonas_disp, opciones_fechas, opciones_cat_interna, categorias_defecto, insumos_disp = [], [], [], [], [], []
fecha_ini_defecto, fecha_fin_defecto = None, None

def recargar_datos():
    global df_m, df_j, df_city, df_nac, df_ext, df_h_cat
    global df_camacol, df_icoced, df_ipc, df_reajuste
    global df_b100_ins, df_b100_cat, df_b100_city, df_b100_nac
    global fechas_disp, zonas_disp, opciones_fechas, opciones_cat_interna, categorias_defecto, insumos_disp
    global fecha_ini_defecto, fecha_fin_defecto
    
    df_insumos = leer_csv_robusto('bd_local_insumos.csv')
    df_pesos = leer_csv_robusto('bd_local_pesos.csv')
    df_precios = leer_csv_robusto('bd_local_precios.csv')
    df_ext = leer_csv_robusto('bd_local_externos.csv')
    df_h_cat = leer_csv_robusto('bd_local_h_cat.csv')

    if not df_precios.empty and not df_insumos.empty and not df_pesos.empty:
        df_insumos['Categoria'] = df_insumos['Categoria'].astype(str).str.upper().str.replace('M,O', 'M.O', case=False).str.strip()
        df_pesos['Categoria'] = df_pesos['Categoria'].astype(str).str.upper().str.replace('M,O', 'M.O', case=False).str.strip()
        df_pesos.loc[df_pesos['Categoria'].isin(['TOTAL M.O.', 'TOTAL M.O', 'TOTAL MANO DE OBRA']), 'Categoria'] = 'TOTAL M.O.'
        
        df_insumos = optimizar_memoria(df_insumos)
        df_pesos = optimizar_memoria(df_pesos)
        df_precios = optimizar_memoria(df_precios)
        
        df_precios['Fecha'] = pd.to_datetime(df_precios['Fecha'], errors='coerce', dayfirst=True)
        df_precios = df_precios.dropna(subset=['Fecha'])
        df_precios['Fecha'] = df_precios['Fecha'].dt.to_period('M').dt.to_timestamp()
        df_precios['Valor_Unitario'] = pd.to_numeric(df_precios['Valor_Unitario'].astype(str).str.replace(',', ''), errors='coerce')
        df_precios = df_precios.groupby(['Ciudad', 'Nombre_Insumo', 'Fecha'], as_index=False, observed=True)['Valor_Unitario'].mean()
        
        df_m = pd.merge(df_precios, df_insumos[['Nombre_Insumo', 'Ciudad', 'Categoria', 'Peso_Insumo_en_Categoria']], on=['Nombre_Insumo', 'Ciudad'], how='inner')
        df_m['Peso_Insumo_en_Categoria'] = pd.to_numeric(df_m['Peso_Insumo_en_Categoria'], errors='coerce')
        df_m = df_m.sort_values(['Ciudad', 'Nombre_Insumo', 'Fecha']).reset_index(drop=True).drop_duplicates(subset=['Ciudad', 'Nombre_Insumo', 'Fecha'])
        
        df_m['Fecha_Mes_Anterior'] = df_m['Fecha'] - pd.DateOffset(months=1)
        df_m['Fecha_Dic_Anterior'] = pd.to_datetime((df_m['Fecha'].dt.year - 1).astype(str) + '-12-01')
        df_m['Fecha_Año_Anterior'] = df_m['Fecha'] - pd.DateOffset(years=1)
        
        df_lookup = df_m[['Ciudad', 'Nombre_Insumo', 'Fecha', 'Valor_Unitario']].copy()
        df_m = pd.merge(df_m, df_lookup.rename(columns={'Fecha': 'Fecha_Mes_Anterior', 'Valor_Unitario': 'Val_Mes_Ant'}), on=['Ciudad', 'Nombre_Insumo', 'Fecha_Mes_Anterior'], how='left')
        df_m = pd.merge(df_m, df_lookup.rename(columns={'Fecha': 'Fecha_Dic_Anterior', 'Valor_Unitario': 'Val_Dic_Ant'}), on=['Ciudad', 'Nombre_Insumo', 'Fecha_Dic_Anterior'], how='left')
        df_m = pd.merge(df_m, df_lookup.rename(columns={'Fecha': 'Fecha_Año_Anterior', 'Valor_Unitario': 'Val_Año_Ant'}), on=['Ciudad', 'Nombre_Insumo', 'Fecha_Año_Anterior'], how='left')
        
        del df_lookup
        gc.collect() # Limpieza activa de RAM
        
        df_m['Var_Mensual_Ins'] = (df_m['Valor_Unitario'] / df_m['Val_Mes_Ant']) - 1
        df_m['Var_Acum_Ins'] = (df_m['Valor_Unitario'] / df_m['Val_Dic_Ant']) - 1
        df_m['Var_Anual_Ins'] = (df_m['Valor_Unitario'] / df_m['Val_Año_Ant']) - 1
        df_m['Var_Mensual_Ins'] = df_m['Var_Mensual_Ins'].replace([np.inf, -np.inf], 0).fillna(0)
        df_m['Var_Acum_Ins'] = df_m['Var_Acum_Ins'].replace([np.inf, -np.inf], 0).fillna(df_m['Var_Mensual_Ins'])
        df_m['Var_Anual_Ins'] = df_m['Var_Anual_Ins'].replace([np.inf, -np.inf], 0).fillna(0)
        
        df_m = optimizar_memoria(df_m) 
        
        # MOTOR 1 (DASHBOARD)
        df_m['Inc_Men_Cat'] = df_m['Var_Mensual_Ins'] * df_m['Peso_Insumo_en_Categoria']
        df_m['Inc_Acum_Cat'] = df_m['Var_Acum_Ins'] * df_m['Peso_Insumo_en_Categoria']
        df_m['Inc_Anual_Cat'] = df_m['Var_Anual_Ins'] * df_m['Peso_Insumo_en_Categoria']
        
        df_c = df_m.groupby(['Fecha', 'Ciudad', 'Categoria'], observed=True)[['Inc_Men_Cat', 'Inc_Acum_Cat', 'Inc_Anual_Cat']].sum().reset_index()
        df_c.columns = ['Fecha', 'Ciudad', 'Categoria', 'Var_Cat_Men', 'Var_Cat_Acum', 'Var_Cat_Anual']
        
        mask_mo = df_c['Categoria'].astype(str).str.contains('M.O', regex=False) | df_c['Categoria'].astype(str).str.contains('MANO DE OBRA', regex=False)
        df_mo_consolidado = df_c[mask_mo].groupby(['Fecha', 'Ciudad'], observed=True).agg({'Var_Cat_Men': lambda x: x[x!=0].mean() if len(x[x!=0])>0 else 0, 'Var_Cat_Acum': lambda x: x[x!=0].mean() if len(x[x!=0])>0 else 0, 'Var_Cat_Anual': lambda x: x[x!=0].mean() if len(x[x!=0])>0 else 0}).reset_index()
        if not df_mo_consolidado.empty:
            df_mo_consolidado['Categoria'] = 'TOTAL M.O.'
            df_c_final = pd.concat([df_c[~mask_mo], df_mo_consolidado], ignore_index=True)
        else: df_c_final = df_c[~mask_mo].copy()
        
        for c in ['Peso_VIS', 'Peso_No_VIS']: df_pesos[c.strip()] = pd.to_numeric(df_pesos[c].astype(str).str.replace(',', '.'), errors='coerce')
        df_j = pd.merge(df_c_final, df_pesos, on=['Ciudad', 'Categoria'], how='inner').reset_index(drop=True)
        
        df_j['Inc_VIS_Men'] = df_j['Var_Cat_Men'] * df_j['Peso_VIS']
        df_j['Inc_VIS_Acum'] = df_j['Var_Cat_Acum'] * df_j['Peso_VIS']
        df_j['Inc_VIS_Anual'] = df_j['Var_Cat_Anual'] * df_j['Peso_VIS']
        
        df_j['Inc_NoVIS_Men'] = df_j['Var_Cat_Men'] * df_j['Peso_No_VIS']
        df_j['Inc_NoVIS_Acum'] = df_j['Var_Cat_Acum'] * df_j['Peso_No_VIS']
        df_j['Inc_NoVIS_Anual'] = df_j['Var_Cat_Anual'] * df_j['Peso_No_VIS']
        
        df_city = df_j.groupby(['Fecha', 'Ciudad'], observed=True)[['Inc_VIS_Acum', 'Inc_NoVIS_Acum', 'Inc_VIS_Men', 'Inc_NoVIS_Men', 'Inc_VIS_Anual', 'Inc_NoVIS_Anual']].sum().reset_index()
        df_city['Tot_City_Acum'] = (df_city['Inc_VIS_Acum'] + df_city['Inc_NoVIS_Acum']) / 2
        df_city['Tot_City_Men'] = (df_city['Inc_VIS_Men'] + df_city['Inc_NoVIS_Men']) / 2
        df_city['Tot_City_Anual'] = (df_city['Inc_VIS_Anual'] + df_city['Inc_NoVIS_Anual']) / 2
        
        df_nac = df_city.groupby('Fecha', observed=True).agg({'Tot_City_Acum': 'mean', 'Tot_City_Men': 'mean', 'Tot_City_Anual': 'mean'}).reset_index()

        gc.collect() # Limpieza activa de RAM

        # MOTOR 2 (BASE 100)
        df_m['Factor_Men_Ins'] = 1 + df_m['Var_Mensual_Ins'].fillna(0)
        df_m['Base100_Ins'] = df_m.groupby(['Ciudad', 'Nombre_Insumo'], observed=True)['Factor_Men_Ins'].cumprod() * 100
        df_b100_ins = df_m[['Fecha', 'Ciudad', 'Categoria', 'Nombre_Insumo', 'Base100_Ins']].copy()

        df_m['B100_x_PesoIns'] = df_m['Base100_Ins'] * df_m['Peso_Insumo_en_Categoria']
        df_b100_cat = df_m.groupby(['Fecha', 'Ciudad', 'Categoria'], observed=True)['B100_x_PesoIns'].sum().reset_index()
        df_b100_cat.rename(columns={'B100_x_PesoIns': 'Base100_Cat'}, inplace=True)
        
        mask_mo_b100 = df_b100_cat['Categoria'].astype(str).str.contains('M.O', regex=False) | df_b100_cat['Categoria'].astype(str).str.contains('MANO DE OBRA', regex=False)
        df_mo_b100 = df_b100_cat[mask_mo_b100].groupby(['Fecha', 'Ciudad'], observed=True)['Base100_Cat'].mean().reset_index()
        if not df_mo_b100.empty:
            df_mo_b100['Categoria'] = 'TOTAL M.O.'
            df_b100_cat = pd.concat([df_b100_cat[~mask_mo_b100], df_mo_b100], ignore_index=True)

        df_b100_cat_p = pd.merge(df_b100_cat, df_pesos[['Ciudad', 'Categoria', 'Peso_VIS', 'Peso_No_VIS']], on=['Ciudad', 'Categoria'], how='inner')
        df_b100_cat_p['Peso_Prom'] = (df_b100_cat_p['Peso_VIS'] + df_b100_cat_p['Peso_No_VIS']) / 2
        df_b100_cat_p['B100_x_PesoCat'] = df_b100_cat_p['Base100_Cat'] * df_b100_cat_p['Peso_Prom']
        df_b100_city = df_b100_cat_p.groupby(['Fecha', 'Ciudad'], observed=True)['B100_x_PesoCat'].sum().reset_index()
        df_b100_city.rename(columns={'B100_x_PesoCat': 'Base100_City'}, inplace=True)

        df_b100_nac = df_b100_city.groupby('Fecha', observed=True)['Base100_City'].mean().reset_index()
        df_b100_nac.rename(columns={'Base100_City': 'Base100_Nac'}, inplace=True)

        del df_precios, df_insumos, df_pesos, df_c, df_c_final, df_b100_cat_p
        gc.collect()

    if not df_ext.empty:
        df_ext = optimizar_memoria(df_ext)
        df_ext['Fecha_Align'] = pd.to_datetime(df_ext['Fecha'], errors='coerce', dayfirst=True).dt.to_period('M').dt.to_timestamp()
        for c in ['Acumulada', 'Mensual', 'Anual']: df_ext[c] = pd.to_numeric(df_ext[c].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0).astype('float32')
        df_ext['Fuente_Up'] = df_ext['Fuente'].astype(str).apply(limpiar_texto)
        df_ext['Cat_Up'] = df_ext['Categoria'].astype(str).apply(limpiar_texto)
        df_ext['Index_Ext'] = 1 + df_ext['Acumulada']
        df_ext_lkp = df_ext[['Fuente_Up', 'Cat_Up', 'Fecha_Align', 'Index_Ext']].copy()
        df_ext['Fecha_Mes_Ant'] = df_ext['Fecha_Align'] - pd.DateOffset(months=1)
        df_ext['Fecha_Año_Ant'] = df_ext['Fecha_Align'] - pd.DateOffset(years=1)
        df_ext = pd.merge(df_ext, df_ext_lkp.rename(columns={'Fecha_Align': 'Fecha_Mes_Ant', 'Index_Ext': 'Idx_Ext_Mes'}), on=['Fuente_Up', 'Cat_Up', 'Fecha_Mes_Ant'], how='left')
        df_ext = pd.merge(df_ext, df_ext_lkp.rename(columns={'Fecha_Align': 'Fecha_Año_Ant', 'Index_Ext': 'Idx_Ext_Año'}), on=['Fuente_Up', 'Cat_Up', 'Fecha_Año_Ant'], how='left')
        df_ext['Mensual'] = (df_ext['Index_Ext'] / df_ext['Idx_Ext_Mes']) - 1
        df_ext['Anual'] = (df_ext['Index_Ext'] / df_ext['Idx_Ext_Año']) - 1
        df_ext['Mensual'] = df_ext['Mensual'].fillna(df_ext['Acumulada'])
        df_ext['Anual'] = df_ext['Anual'].fillna(0.0)
        
        df_camacol = df_ext[(df_ext['Fuente_Up'].str.contains('CAMACOL', na=False)) & (df_ext['Cat_Up'].str.contains('COSTO TOTA', na=False))].sort_values('Fecha_Align').drop_duplicates(subset=['Fecha_Align'], keep='last')
        df_icoced = df_ext[(df_ext['Fuente_Up'].str.contains('ICOCED', na=False)) & (df_ext['Cat_Up'].str.contains('ICOCED', na=False))].sort_values('Fecha_Align').drop_duplicates(subset=['Fecha_Align'], keep='last')
        df_ipc = df_ext[(df_ext['Fuente_Up'].str.contains('IPC', na=False)) & (df_ext['Cat_Up'].str.contains('IPC', na=False))].sort_values('Fecha_Align').drop_duplicates(subset=['Fecha_Align'], keep='last')
        df_reajuste = df_ext[df_ext['Fuente_Up'].str.contains('REAJUSTE', na=False)].sort_values('Fecha_Align').drop_duplicates(subset=['Fecha_Align'], keep='last')

    fechas_todas = set()
    if not df_nac.empty: fechas_todas.update(df_nac['Fecha'].dropna().tolist())
    if not df_ext.empty: fechas_todas.update(df_ext['Fecha_Align'].dropna().tolist())

    fechas_disp = sorted(list(fechas_todas))
    zonas_disp = ["Nacional (Promedio)"] + list(df_city['Ciudad'].dropna().unique()) if not df_city.empty else []

    if fechas_disp:
        fecha_fin_defecto = fechas_disp[-1] 
        idx_ini = len(fechas_disp) - 13 if len(fechas_disp) >= 13 else 0
        fecha_ini_defecto = fechas_disp[idx_ini] 
    else:
        fecha_ini_defecto, fecha_fin_defecto = None, None

    opciones_fechas = [{'label': pd.to_datetime(x).strftime('%B %Y').capitalize(), 'value': x} for x in fechas_disp]

    if not df_h_cat.empty:
        col_con_temp = 'Categoria_Coninsa' if 'Categoria_Coninsa' in df_h_cat.columns else df_h_cat.columns[0]
        opciones_cat_interna = sorted(df_h_cat[col_con_temp].dropna().unique())
        nombres_deseados = ["TOTAL M.O.", "ADMINSITRACION (PERSONAL DE OBRA)", "RESTO DE COSTOS", "TOTAL CEMENTO", "TOTAL HIERRO", "TOTAL INSTALACIONES ELECTRICAS", "TOTAL PINTURA", "TOTAL CIELOS RASOS Y DIVISIONES", "TOTAL CARPINTERIA METALICA", "TOTAL CONCRETO PREMEZCLADO Y MORTEROS", "TOTAL EQUIPOS ESPECIALES (COMO: ASCENSORES)", "TOTAL INSTALACIONES HIDRAULICAS Y DE GAS"]
        categorias_defecto = [cat for cat in opciones_cat_interna if str(cat).strip().upper() in nombres_deseados]
        if len(categorias_defecto) == 0: categorias_defecto = opciones_cat_interna

    insumos_disp = sorted(df_m['Nombre_Insumo'].dropna().unique()) if not df_m.empty else []
    gc.collect()

recargar_datos()

config_graficas = {'displayModeBar': True, 'displaylogo': False, 'modeBarButtonsToRemove': ['lasso2d', 'select2d']}

def serve_layout():
    header_global = dbc.Row([
        dbc.Col(html.Div([
            html.Img(src="https://www.coninsa.co/themes/custom/coninsa/logo.svg", height="45px", style={'marginRight': '20px'}),
            html.H4("Plataforma Gerencial de Costos", className="fw-bold", style={'color': C_AZUL, 'margin': 0, 'display': 'inline-block'})
        ], style={'display': 'flex', 'alignItems': 'center'}), width=7),
        dbc.Col(dbc.InputGroup([
            dbc.InputGroupText("📅 Desde:", style={'fontWeight':'bold', 'backgroundColor':C_AZUL, 'color':'white'}),
            dbc.Select(id='filtro_fecha_inicio', options=opciones_fechas, value=fecha_ini_defecto),
            dbc.InputGroupText("Hasta:", style={'fontWeight':'bold', 'backgroundColor':C_AZUL, 'color':'white'}),
            dbc.Select(id='filtro_fecha_fin', options=opciones_fechas, value=fecha_fin_defecto)
        ], size="sm"), width=5)
    ], className="mb-3 p-3", style={'backgroundColor': 'white', 'borderRadius': '10px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.04)'})

    layout_dashboard = html.Div([
        dbc.Row([
            dbc.Col([html.Label("📍 Zona:", style={'fontSize':'12px', 'fontWeight':'bold', 'color': C_AZUL}), dbc.Select(id='filtro_zona', options=[{'label': x, 'value': x} for x in zonas_disp], value=zonas_disp[0] if zonas_disp else None)], width=4),
            dbc.Col([html.Label("📉 Métrica:", style={'fontSize':'12px', 'fontWeight':'bold', 'color': C_AZUL}), dbc.Select(id='filtro_metrica', options=[{'label': x, 'value': x} for x in ["Acumulada", "Mensual", "Anual"]], value="Acumulada")], width=4),
            dbc.Col([html.Label("📊 Años Barras:", style={'fontSize':'12px', 'fontWeight':'bold', 'color': C_AZUL}), dbc.Select(id='filtro_anios_barras', options=[{'label': str(x), 'value': x} for x in [3,4,5,6,7]], value=5)], width=4),
        ], className="mb-3 p-3", style={'backgroundColor': 'white', 'borderRadius': '10px'}),
        dbc.Row(id='tarjetas_kpi', className="mb-3"),
        dbc.Row([dbc.Col(dcc.Graph(id='graf_lineas', style={'height': '45vh'}), width=7), dbc.Col(dcc.Graph(id='graf_barras', style={'height': '45vh'}), width=5)], className="mb-3"),
        dbc.Row([dbc.Col(dcc.Graph(id='graf_burbujas', style={'height': '45vh'}), width=7), dbc.Col(dcc.Graph(id='graf_top', style={'height': '45vh'}), width=5)])
    ])

    layout_tablas = html.Div([
        dbc.Row([dbc.Col(html.H6(id="titulo_tabla_mensual", className="text-center fw-bold p-2 text-white", style={'backgroundColor': C_AZUL, 'borderRadius': '8px'}), width=6), dbc.Col(html.H6(id="titulo_tabla_acumulada", className="text-center fw-bold p-2 text-white", style={'backgroundColor': C_AZUL, 'borderRadius': '8px'}), width=6)]),
        dbc.Row([dbc.Col(html.Div(id="contenedor_tabla_mensual"), width=6), dbc.Col(html.Div(id="contenedor_tabla_acumulada"), width=6)])
    ])

    layout_matriz = html.Div([
        dbc.Row(dbc.Col([html.H6("1️⃣ Nivel 1: Resumen por Categorías", className="text-center fw-bold p-2 text-white mb-0", style={'backgroundColor': C_AZUL, 'borderRadius': '8px 8px 0 0'}), html.Div(id="contenedor_tabla_matriz", className="mt-2")], width=12), className="mb-3"),
        dbc.Row([
            dbc.Col([html.H6(id="titulo_detalle_insumos", children="2️⃣ Nivel 2: Detalle de Insumos", className="text-center fw-bold p-2 text-white mb-0", style={'backgroundColor': C_TEAL, 'borderRadius': '8px 8px 0 0'}), html.Div(id="contenedor_detalle_insumos", className="mt-2")], width=7),
            dbc.Col([html.H6(id="titulo_precios_insumo", children="3️⃣ Nivel 3: Auditoría y Edición", className="text-center fw-bold p-2 text-white mb-0", style={'backgroundColor': C_VERDE, 'borderRadius': '8px 8px 0 0'}), html.Div(id="contenedor_precios_insumo", className="mt-2"), html.Button("💾 Guardar Cambios", id="btn_guardar_datos", className="btn mt-2 fw-bold text-white", style={'backgroundColor': C_VERDE, 'width': '100%'}), html.Div(id="msg_guardado", className="mt-2")], width=5)
        ])
    ])

    layout_comparativo = html.Div([
        dbc.Row([
            dbc.Col([html.Label("🔍 Categoría:", style={'fontSize':'12px', 'fontWeight':'bold', 'color':C_AZUL}), dcc.Dropdown(id='filtro_categoria_interna', options=[{'label': str(x).title(), 'value': x} for x in opciones_cat_interna], value=categorias_defecto, multi=True)], width=8),
            dbc.Col([html.Label("📍 Zona:", style={'fontSize':'12px', 'fontWeight':'bold', 'color':C_AZUL}), dbc.Select(id='filtro_zona_comp', options=[{'label': x, 'value': x} for x in zonas_disp], value=zonas_disp[0] if zonas_disp else None)], width=4)
        ], className="mb-3 p-3 bg-white rounded"),
        dbc.Row(dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(id='graf_comparativo_barras_agrupadas', style={'height': '70vh'}))), width=12))
    ])

    layout_analisis = html.Div([
        dbc.Row([
            dbc.Col([html.Label("🔍 Insumo (Predicción IA):", style={'fontSize':'12px', 'fontWeight':'bold', 'color':C_AZUL}), dcc.Dropdown(id='filtro_insumo_detalle', options=[{'label': str(x).title(), 'value': x} for x in insumos_disp], value=insumos_disp[0] if insumos_disp else None)], width=8),
            dbc.Col([html.Label("📍 Zona:", style={'fontSize':'12px', 'fontWeight':'bold', 'color':C_AZUL}), dbc.Select(id='filtro_zona_insumo', options=[{'label': x, 'value': x} for x in zonas_disp], value=zonas_disp[0] if zonas_disp else None)], width=4)
        ], className="mb-3 p-3 bg-white rounded"),
        dbc.Row(dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(id='graf_insumo_precio', style={'height': '35vh'}))), width=12), className="mb-3"),
        dbc.Row(dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(id='graf_insumo_variacion', style={'height': '35vh'}))), width=12))
    ])

    layout_informe = html.Div([
        dbc.Row(dbc.Col(html.Button("🖨️ Descargar PDF / Imprimir", id="btn_imprimir", className="btn btn-lg fw-bold shadow-sm text-white", style={'backgroundColor': C_VERDE, 'width': '100%', 'marginBottom': '20px'}), width={"size": 6, "offset": 3})),
        html.Div(id="contenedor_reporte_pdf", className="hoja-papel")
    ])

    layout_simulador = html.Div([
        dbc.Row(dbc.Col(html.H5("🎛️ Simulador Macro de Escenarios (What-If)", className="fw-bold", style={'color': C_AZUL}), width=12), className="mb-2"),
        dbc.Row([
            dbc.Col(dbc.Alert([
                html.H6("¿Qué hace este simulador?", className="alert-heading fw-bold"),
                html.P("Esta herramienta te permite jugar con el futuro. Modifica los porcentajes de variación de los insumos más críticos (Mano de Obra, Acero y Cemento) para simular escenarios hipotéticos en el mercado."),
                html.Hr(),
                html.P("¿Cómo lo calcula matemáticamente?", className="fw-bold mb-1"),
                html.Small("El motor de la app toma la estructura de costos real de tu último corte e inyecta las variaciones que elijas en los sliders directamente sobre esas categorías específicas. Luego, recalcula el impacto total ponderado (VIS y No VIS) en el Costo Directo. Así puedes anticipar cómo un alza repentina afectará el P&L general de Coninsa.")
            ], color="info"), width=12)
        ], className="mb-3"),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Label("Variación Mano de Obra (%)", className="fw-bold"),
                dcc.Slider(id='sim_mo', min=-20, max=20, step=0.5, value=0, marks={i: f"{i}%" for i in range(-20, 21, 5)}, tooltip={"placement": "bottom"}),
                html.Br(),
                html.Label("Variación Acero / Hierro (%)", className="fw-bold"),
                dcc.Slider(id='sim_acero', min=-20, max=20, step=0.5, value=0, marks={i: f"{i}%" for i in range(-20, 21, 5)}, tooltip={"placement": "bottom"}),
                html.Br(),
                html.Label("Variación Cemento (%)", className="fw-bold"),
                dcc.Slider(id='sim_cemento', min=-20, max=20, step=0.5, value=0, marks={i: f"{i}%" for i in range(-20, 21, 5)}, tooltip={"placement": "bottom"})
            ]), className="shadow-sm"), width=5),
            dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(id='graf_simulador', style={'height': '50vh'})), className="shadow-sm"), width=7)
        ])
    ])

    layout_chatbot = html.Div([
        dbc.Row(dbc.Col(html.H5("💬 Asistente IA Avanzado (Google Gemini)", className="fw-bold", style={'color': C_AZUL}), width=12), className="mb-3"),
        dbc.Row(dbc.Col(dbc.Card(dbc.CardBody([
            dbc.InputGroup([
                dbc.Input(id="input_chat", placeholder="Hazle cualquier pregunta sobre la totalidad de tus insumos a Gemini...", type="text"),
                dbc.Button("Preguntar a Gemini ✨", id="btn_chat", color="primary")
            ]),
            html.Hr(),
            dcc.Loading(id="loading-chat", type="dot", color="#8B5CF6", children=[
                html.Div(id="output_chat", style={'minHeight': '200px', 'backgroundColor': C_GRIS_BG, 'padding': '15px', 'borderRadius': '5px', 'fontSize': '15px'})
            ])
        ]), className="shadow-sm"), width=10, style={'margin': 'auto'}))
    ])

    layout_base100 = html.Div([
        dbc.Row(dbc.Col(html.H5("💯 Índice Base 100 (Evolución Compuesta Histórica)", className="fw-bold", style={'color': C_AZUL}), width=12), className="mb-2"),
        dbc.Row([
            dbc.Col([
                html.Label("Nivel de Análisis:", style={'fontSize':'12px', 'fontWeight':'bold', 'color':C_AZUL}),
                dbc.Select(id='b100_nivel', options=[
                    {'label': 'Nacional (Consolidado)', 'value': 'nac'},
                    {'label': 'Por Ciudad', 'value': 'city'},
                    {'label': 'Por Categoría', 'value': 'cat'},
                    {'label': 'Por Insumo', 'value': 'ins'}
                ], value='nac')
            ], width=3),
            dbc.Col([
                html.Label("Filtro 1 (Ciudad):", style={'fontSize':'12px', 'fontWeight':'bold', 'color':C_AZUL}),
                dcc.Dropdown(id='b100_filtro1', placeholder="Seleccione Ciudad...", disabled=True)
            ], width=4),
            dbc.Col([
                html.Label("Filtro 2 (Categoría / Insumo):", style={'fontSize':'12px', 'fontWeight':'bold', 'color':C_AZUL}),
                dcc.Dropdown(id='b100_filtro2', placeholder="Seleccione Ítem...", disabled=True)
            ], width=5)
        ], className="mb-3 p-3 bg-white rounded shadow-sm"),
        dbc.Row(dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(id='graf_base100', style={'height': '45vh'})), className="shadow-sm"), width=12), className="mb-3"),
        
        dbc.Row(dbc.Col(html.H5("📥 Tablas Generales Base 100 (Exportables a Excel)", className="fw-bold mt-4", style={'color': C_VERDE}), width=12)),
        dbc.Tabs([
            dbc.Tab(html.Div(id='tbl_b100_nac', className="mt-3"), label="🌎 Nacional"),
            dbc.Tab(html.Div(id='tbl_b100_city', className="mt-3"), label="🏙️ Ciudades"),
            dbc.Tab(html.Div(id='tbl_b100_cat', className="mt-3"), label="🏗️ Categorías"),
            dbc.Tab(html.Div(id='tbl_b100_ins', className="mt-3"), label="🔩 Insumos"),
        ])
    ])

    layout_incidencias = html.Div([
        dbc.Row(dbc.Col(html.H5("🔎 Auditoría de Incidencias (Verificación Matemática)", className="fw-bold", style={'color': C_AZUL}), width=12), className="mb-2"),
        dbc.Row(dbc.Col(html.P("Esta tabla detalla matemáticamente el impacto de cada categoría. Fórmula: Variación de la Categoría × Peso Promedio = Incidencia en la Ciudad.", className="text-muted"), width=12), className="mb-3"),
        dbc.Row(dbc.Col(html.Div(id="tbl_incidencias_auditoria"), width=12))
    ])

    tabs = dbc.Tabs([
        dbc.Tab(layout_dashboard, label="📊 1. Dashboard", tab_id="t1"),
        dbc.Tab(layout_tablas, label="📋 2. Resumen", tab_id="t2"),
        dbc.Tab(layout_matriz, label="🧮 3. Matriz", tab_id="t3"),
        dbc.Tab(layout_comparativo, label="📈 4. Comparativo", tab_id="t4"),
        dbc.Tab(layout_analisis, label="🔬 5. Predicción", tab_id="t5"),
        dbc.Tab(layout_informe, label="📄 6. Informe PDF", tab_id="t6", label_style={'color': C_VERDE, 'fontWeight': 'bold'}),
        dbc.Tab(layout_simulador, label="🎛️ 7. Simulador", tab_id="t7", label_style={'color': C_AMARILLO_REA, 'fontWeight': 'bold'}),
        dbc.Tab(layout_chatbot, label="✨ 8. Gemini IA", tab_id="t8", label_style={'color': '#8B5CF6', 'fontWeight': 'bold'}),
        dbc.Tab(layout_base100, label="💯 9. Base 100", tab_id="t9", label_style={'color': C_TEAL, 'fontWeight': 'bold'}),
        dbc.Tab(layout_incidencias, label="🔎 10. Incidencias", tab_id="t10", label_style={'color': '#d97706', 'fontWeight': 'bold'}) 
    ], active_tab="t1", className="mb-3")

    return dbc.Container([header_global, tabs], fluid=True, style={'backgroundColor': C_GRIS_BG, 'minHeight': '100vh', 'padding': '15px 25px'})

app.layout = serve_layout

app.clientside_callback(
    "function(n_clicks) { if(n_clicks > 0) { window.print(); } return window.dash_clientside.no_update; }",
    Output('btn_imprimir', 'id'), Input('btn_imprimir', 'n_clicks'), prevent_initial_call=True
)

@app.callback(
    [Output("titulo_tabla_mensual", "children"), Output("titulo_tabla_acumulada", "children"), Output("contenedor_tabla_mensual", "children"), Output("contenedor_tabla_acumulada", "children")],
    [Input("filtro_fecha_fin", "value")]
)
def actualizar_tablas(fecha_sel):
    if not fecha_sel or df_j.empty: raise dash.exceptions.PreventUpdate
    dt = pd.to_datetime(fecha_sel)
    df_f = df_j[df_j['Fecha'] <= dt]
    if df_f.empty: return "", "", html.Div(), html.Div()
    fe = df_f['Fecha'].max()
    df_b = df_j[df_j['Fecha'] == fe].copy()
    df_b['Peso_Promedio'] = (df_b['Peso_VIS'] + df_b['Peso_No_VIS']) / 2 if 'Peso_Promedio' not in df_b.columns else df_b['Peso_Promedio']
    
    pivot_m = df_b.pivot_table(index='Categoria', columns='Ciudad', values='Var_Cat_Men', aggfunc='mean')
    pivot_m['Nacional'] = pivot_m.mean(axis=1)
    pivot_m.insert(0, '% Peso', df_b.groupby('Categoria')['Peso_Promedio'].mean())
    pivot_m = pivot_m.reset_index().sort_values('% Peso', ascending=False)
    
    pivot_a = df_b.pivot_table(index='Categoria', columns='Ciudad', values='Var_Cat_Acum', aggfunc='mean')
    pivot_a['Nacional'] = pivot_a.mean(axis=1)
    pivot_a.insert(0, '% Peso', df_b.groupby('Categoria')['Peso_Promedio'].mean())
    pivot_a = pivot_a.reset_index().sort_values('% Peso', ascending=False)
    
    fmt = Format(scheme=Scheme.percentage, precision=2)
    def gen_t(df_t):
        cols = [{'name': str(c), 'id': str(c)} if c == 'Categoria' else {'name': str(c), 'id': str(c), 'type': 'numeric', 'format': fmt} for c in df_t.columns]
        cond = [{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8FAFC'}]
        for c in df_t.columns:
            if c not in ['Categoria', '% Peso']: cond.extend([{'if': {'filter_query': f'{{{c}}} < -0.0001', 'column_id': c}, 'color': C_VERDE, 'fontWeight': 'bold'}, {'if': {'filter_query': f'{{{c}}} > 0.0001', 'column_id': c}, 'color': '#e11d48', 'fontWeight': 'bold'}])
        
        return dash_table.DataTable(
            data=df_t.to_dict('records'), columns=cols, style_data_conditional=cond, 
            style_cell={'fontSize':'11px', 'textAlign':'center'},
            export_format='xlsx', export_headers='display'
        )
    return f"Variación Mensual - {fe.strftime('%b %Y')}", f"Variación Acumulada - {fe.strftime('%b %Y')}", gen_t(pivot_m), gen_t(pivot_a)

@app.callback(Output("contenedor_tabla_matriz", "children"), [Input("filtro_fecha_fin", "value")])
def actualizar_matriz(fecha_sel):
    if not fecha_sel or df_j.empty: raise dash.exceptions.PreventUpdate
    fe = df_j[df_j['Fecha'] <= pd.to_datetime(fecha_sel)]['Fecha'].max()
    df_b = df_j[df_j['Fecha'] == fe].copy()
    ciudades = sorted(df_b['Ciudad'].dropna().unique())
    df_mat = pd.DataFrame({'Categoria': sorted(df_b['Categoria'].dropna().unique())})
    df_mat['id'] = df_mat['Categoria']
    for c in ciudades:
        d = df_b[df_b['Ciudad']==c].set_index('Categoria')
        df_mat[f'Men. {c}'] = df_mat['Categoria'].map(d['Var_Cat_Men'])
        df_mat[f'Acum. {c}'] = df_mat['Categoria'].map(d['Var_Cat_Acum'])
        df_mat[f'YoY. {c}'] = df_mat['Categoria'].map(d['Var_Cat_Anual'])
    fmt = Format(scheme=Scheme.percentage, precision=2)
    cols = [{'name': str(c), 'id': str(c)} if c == 'Categoria' else {'name': str(c), 'id': str(c), 'type': 'numeric', 'format': fmt} for c in df_mat.columns if c != 'id']
    return dash_table.DataTable(
        id='tabla_matriz_principal', data=df_mat.to_dict('records'), columns=cols, 
        style_data={'cursor':'pointer'}, 
        style_cell={'fontSize':'10px', 'textAlign':'center', 'padding': '5px', 'minWidth': '95px'},
        style_table={'overflowX': 'auto'}
    )

@app.callback(
    [Output("titulo_detalle_insumos", "children"), Output("contenedor_detalle_insumos", "children")], 
    [Input("tabla_matriz_principal", "active_cell")], 
    [State("tabla_matriz_principal", "data"), State("filtro_fecha_fin", "value")]
)
def detalle_insumos(ac, data_matriz, fs):
    if not ac or not fs or not data_matriz: return "2️⃣ Nivel 2: Detalle de Insumos", html.Div(html.H6("👈 Selecciona una Categoría arriba", className="text-center text-muted mt-5"))
    
    cat = ac.get('row_id')
    if not cat: cat = data_matriz[ac['row']].get('Categoria')
    if not cat: return "Detalle Insumos", html.Div()
    
    fe = df_m[df_m['Fecha'] <= pd.to_datetime(fs)]['Fecha'].max()
    df_b = df_m[(df_m['Fecha']==fe)&(df_m['Categoria']==cat)]
    if df_b.empty: return f"Detalle: {cat}", html.Div("No hay datos para esta categoría.")
    
    df_i = pd.DataFrame({'Insumo': sorted(df_b['Nombre_Insumo'].dropna().unique())})
    df_i['id'] = df_i['Insumo']
    for c in df_b['Ciudad'].dropna().unique():
        d = df_b[df_b['Ciudad']==c].set_index('Nombre_Insumo')
        df_i[f'Precio {c}'] = df_i['Insumo'].map(d['Valor_Unitario'])
        df_i[f'Men. {c}'] = df_i['Insumo'].map(d['Var_Mensual_Ins'])
        df_i[f'Acum. {c}'] = df_i['Insumo'].map(d['Var_Acum_Ins'])
        df_i[f'YoY. {c}'] = df_i['Insumo'].map(d['Var_Anual_Ins'])
        
    fmt_p = Format(scheme=Scheme.percentage, precision=2)
    fmt_u = Format(scheme=Scheme.fixed, precision=0, group=Group.yes, groups=3, symbol=Symbol.yes, symbol_prefix='$ ')
    
    cols = []
    for c in df_i.columns:
        if c == 'Insumo': cols.append({'name': str(c), 'id': str(c)})
        elif 'Precio' in c: cols.append({'name': str(c), 'id': str(c), 'type': 'numeric', 'format': fmt_u})
        elif c != 'id': cols.append({'name': str(c), 'id': str(c), 'type': 'numeric', 'format': fmt_p})
        
    return f"Detalle: {cat}", dash_table.DataTable(
        id='tabla_insumos_drill', data=df_i.to_dict('records'), columns=cols, 
        style_data={'cursor':'pointer'}, 
        style_cell={'fontSize':'10px', 'textAlign':'center', 'padding': '5px', 'minWidth': '95px'},
        style_table={'overflowX': 'auto'}
    )

@app.callback(
    [Output("titulo_precios_insumo", "children"), Output("contenedor_precios_insumo", "children")], 
    [Input("tabla_insumos_drill", "active_cell")], 
    [State("tabla_insumos_drill", "data"), State("filtro_fecha_fin", "value")]
)
def precios_insumos(ac, data_insumos, fs):
    if not ac or not fs or not data_insumos: return "3️⃣ Nivel 3: Auditoría y Edición", html.Div(html.H6("👈 Selecciona un Insumo a la izquierda", className="text-center text-muted mt-5"))
    
    ins = ac.get('row_id')
    if not ins: ins = data_insumos[ac['row']].get('Insumo')
    if not ins: return "Edición", html.Div()
    
    fe = df_m[df_m['Fecha'] <= pd.to_datetime(fs)]['Fecha'].max()
    df_b = df_m[(df_m['Fecha']==fe)&(df_m['Nombre_Insumo']==ins)][['Ciudad','Val_Mes_Ant','Valor_Unitario','Var_Mensual_Ins']]
    df_b.columns = ['Ciudad','Precio Ant.','Precio Actual','Var Mensual']
    
    df_obs = leer_csv_robusto('bd_local_observaciones.csv')
    df_b['Observacion'] = df_b['Ciudad'].map(df_obs[df_obs['Nombre_Insumo']==ins].set_index('Ciudad')['Observacion']) if not df_obs.empty and 'Observacion' in df_obs.columns else ""
    df_b['Observacion'] = df_b['Observacion'].fillna("")
    
    fmt_u = Format(scheme=Scheme.fixed, precision=0, group=Group.yes, groups=3, symbol=Symbol.yes, symbol_prefix='$ ')
    fmt_p = Format(scheme=Scheme.percentage, precision=2)
    cols = [
        {'name':'Ciudad', 'id':'Ciudad', 'editable':False}, 
        {'name':'Precio Ant.', 'id':'Precio Ant.', 'type':'numeric', 'format':fmt_u, 'editable':False}, 
        {'name':'Precio Actual (Editar)', 'id':'Precio Actual', 'type':'numeric', 'format':fmt_u, 'editable':True}, 
        {'name':'Obs (Editar)', 'id':'Observacion', 'editable':True}, 
        {'name':'Var Mensual', 'id':'Var Mensual', 'type':'numeric', 'format':fmt_p, 'editable':False}
    ]
    return f"Editar: {ins[:30]}", dash_table.DataTable(
        id='tabla_precios_nivel_3', data=df_b.to_dict('records'), columns=cols, 
        style_cell_conditional=[{'if':{'column_id':'Precio Actual'}, 'backgroundColor':'#fef3c7'}], 
        style_cell={'fontSize':'10px', 'textAlign':'center', 'padding': '5px', 'minWidth': '95px'},
        style_table={'overflowX': 'auto'}
    )

@app.callback(
    Output('msg_guardado', 'children'), 
    Input('btn_guardar_datos', 'n_clicks'), 
    State('tabla_precios_nivel_3', 'data'), 
    State('tabla_insumos_drill', 'active_cell'), 
    State('tabla_insumos_drill', 'data'),
    State('filtro_fecha_fin', 'value'), 
    prevent_initial_call=True
)
def guardar_datos(nc, data, ac, data_insumos, fs):
    if not nc or not data or not ac or not data_insumos: raise dash.exceptions.PreventUpdate
    ins = ac.get('row_id')
    if not ins: ins = data_insumos[ac['row']].get('Insumo')
    
    dt = pd.to_datetime(fs)
    obs_r, pr_r = [], []
    for r in data:
        obs_r.append({'Nombre_Insumo':ins, 'Ciudad':r['Ciudad'], 'Observacion':r['Observacion']})
        pr_r.append({'Ciudad':r['Ciudad'], 'Nombre_Insumo':ins, 'Fecha':dt, 'Valor_Unitario':r['Precio Actual']})
    
    dfo = leer_csv_robusto('bd_local_observaciones.csv')
    if not dfo.empty: dfo = dfo[~(dfo['Nombre_Insumo']==ins)]; dfo = pd.concat([dfo, pd.DataFrame(obs_r)])
    else: dfo = pd.DataFrame(obs_r)
    dfo.to_csv('bd_local_observaciones.csv', sep=';', index=False, encoding='utf-8-sig')
    guardar_en_github(dfo, 'bd_local_observaciones.csv', f"Obs: {ins}")
    
    dfp = leer_csv_robusto('bd_local_precios.csv')
    if not dfp.empty:
        dfp['ft'] = pd.to_datetime(dfp['Fecha'], dayfirst=True).dt.to_period('M').dt.to_timestamp()
        for p in pr_r:
            m = (dfp['Nombre_Insumo']==ins)&(dfp['Ciudad']==p['Ciudad'])&(dfp['ft']==dt.replace(day=1))
            if m.any(): dfp.loc[m, 'Valor_Unitario'] = p['Valor_Unitario']
            else: dfp = pd.concat([dfp, pd.DataFrame([{'Ciudad':p['Ciudad'],'Nombre_Insumo':ins,'Fecha':dt.strftime('%d/%m/%Y'),'Valor_Unitario':p['Valor_Unitario']}])])
        dfp = dfp.drop(columns=['ft'])
        dfp.to_csv('bd_local_precios.csv', sep=';', index=False, encoding='utf-8-sig')
        guardar_en_github(dfp, 'bd_local_precios.csv', f"Precio: {ins}")
    
    recargar_datos() 
    return dbc.Alert("✅ Guardado en GitHub. ¡Presiona F5 para actualizar!", color="success", duration=5000)

@app.callback(Output("contenedor_reporte_pdf", "children"), [Input("filtro_fecha_fin", "value")])
def reporte_pdf(fs):
    if not fs or df_j.empty: raise dash.exceptions.PreventUpdate
    fe = df_j[df_j['Fecha'] <= pd.to_datetime(fs)]['Fecha'].max()
    df_b = df_j[df_j['Fecha'] == fe].copy()
    if 'Peso_Promedio' not in df_b: df_b['Peso_Promedio'] = (df_b['Peso_VIS']+df_b['Peso_No_VIS'])/2
    
    pm = df_b.pivot_table(index='Categoria', columns='Ciudad', values='Var_Cat_Men', aggfunc='mean').reset_index()
    fmt = Format(scheme=Scheme.percentage, precision=2)
    t1 = dash_table.DataTable(data=pm.to_dict('records'), columns=[{'name':str(c), 'id':str(c)} if c=='Categoria' else {'name':str(c), 'id':str(c), 'type':'numeric', 'format':fmt} for c in pm.columns])
    
    secciones = []
    for c in [x for x in df_city['Ciudad'].dropna().unique() if x != "Nacional (Promedio)"]:
        d_c = df_m[(df_m['Fecha']==fe)&(df_m['Ciudad']==c)]
        al = d_c.sort_values('Var_Mensual_Ins', ascending=False).head(10)[['Nombre_Insumo','Var_Mensual_Ins']]
        ba = d_c.sort_values('Var_Mensual_Ins', ascending=True).head(10)[['Nombre_Insumo','Var_Mensual_Ins']]
        cols = [{'name':'Insumo','id':'Nombre_Insumo'}, {'name':'Var','id':'Var_Mensual_Ins','type':'numeric','format':fmt}]
        secciones.append(html.Div(className="salto-pagina", children=[
            html.H3(f"📍 {c}"), html.H5("📈 TOP ALZAS"), dash_table.DataTable(data=al.to_dict('records'), columns=cols), html.H5("📉 TOP BAJAS"), dash_table.DataTable(data=ba.to_dict('records'), columns=cols)
        ]))
    return html.Div(id="zona-impresion", children=[html.H2("INFORME EJECUTIVO DE COSTOS"), html.H4(f"Mes: {fe.strftime('%B %Y')}"), t1] + secciones)

@app.callback(Output('graf_simulador', 'figure'), [Input('sim_mo', 'value'), Input('sim_acero', 'value'), Input('sim_cemento', 'value'), Input('filtro_fecha_fin', 'value')])
def simulador(smo, sac, sce, fs):
    if df_j.empty or not fs: return go.Figure()
    fe = df_j[df_j['Fecha'] <= pd.to_datetime(fs)]['Fecha'].max()
    db = df_j[df_j['Fecha'] == fe].copy()
    
    def aplicar(row):
        cat = str(row['Categoria']).upper()
        if 'M.O' in cat or 'MANO DE OBRA' in cat: return row['Var_Cat_Acum'] + (smo/100)
        if 'HIERRO' in cat or 'ACERO' in cat: return row['Var_Cat_Acum'] + (sac/100)
        if 'CEMENTO' in cat: return row['Var_Cat_Acum'] + (sce/100)
        return row['Var_Cat_Acum']
        
    db['Simulado'] = db.apply(aplicar, axis=1)
    db['Peso_Prom'] = (db['Peso_VIS'] + db['Peso_No_VIS'])/2
    
    real = (db['Var_Cat_Acum'] * db['Peso_Prom']).sum()
    sim = (db['Simulado'] * db['Peso_Prom']).sum()
    
    fig = go.Figure(data=[
        go.Bar(name='Real Acumulado', x=['Costo Total'], y=[real], marker_color=C_AZUL, text=[f"{real:+.2%}"], textposition='auto'),
        go.Bar(name='Simulado (What-If)', x=['Costo Total'], y=[sim], marker_color=C_AMARILLO_REA, text=[f"{sim:+.2%}"], textposition='auto')
    ])
    fig.update_layout(title="Comparativa Impacto en Costo Directo Total", template="plotly_white", barmode='group', yaxis_tickformat='.1%')
    return fig

@app.callback(Output('output_chat', 'children'), Input('btn_chat', 'n_clicks'), State('input_chat', 'value'), State('filtro_fecha_fin', 'value'), prevent_initial_call=True)
def chatbot_gemini(nc, txt, fs):
    # OPTIMIZACIÓN: Carga Perezosa (Lazy Loading) de IA solo al usarla
    import google.generativeai as genai
    
    if not txt or df_m.empty: return "Por favor, escribe una pregunta."
    
    fe = df_m[df_m['Fecha'] <= pd.to_datetime(fs)]['Fecha'].max()
    d = df_m[df_m['Fecha'] == fe]
    
    try:
        d_ins = d[['Ciudad', 'Categoria', 'Nombre_Insumo', 'Val_Mes_Ant', 'Valor_Unitario', 'Var_Mensual_Ins']].copy()
        
        d_ins['Val_Mes_Ant'] = d_ins['Val_Mes_Ant'].apply(lambda x: f"${x:,.0f}" if pd.notnull(x) else "$0")
        d_ins['Valor_Unitario'] = d_ins['Valor_Unitario'].apply(lambda x: f"${x:,.0f}" if pd.notnull(x) else "$0")
        d_ins['Var_Mensual_Ins'] = (d_ins['Var_Mensual_Ins'] * 100).round(2).astype(str) + '%'
        
        csv_completo = d_ins.to_csv(index=False, sep='|')
        promedio_nac = df_nac[df_nac['Fecha'] == fe]['Tot_City_Men'].values[0] if not df_nac[df_nac['Fecha'] == fe].empty else 0.0
        
        contexto = f"PERIODO DE ANÁLISIS: {fe.strftime('%B %Y')}.\n"
        contexto += f"Variación Promedio Nacional: {promedio_nac*100:.2f}%.\n\n"
        contexto += "A continuación se proporciona la lista COMPLETA de TODOS los insumos de Coninsa para este mes (Formato: Ciudad|Categoria|Nombre_Insumo|Precio_Anterior|Precio_Actual|Var_Mensual):\n"
        contexto += csv_completo
        
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
            
        prompt = (
            f"Eres un analista financiero experto en costos de construcción de la empresa Coninsa.\n"
            f"Tienes acceso a la base de datos COMPLETA de insumos de la empresa para el periodo seleccionado.\n"
            f"Usa la siguiente información completa para responder con total precisión sobre CUALQUIER insumo, categoría o ciudad solicitada:\n\n"
            f"{contexto}\n\n"
            f"Pregunta del usuario: {txt}\n\n"
            f"Instrucciones de respuesta: Sé profesional, claro, analítico y directo. Puedes revisar y mencionar cualquier insumo contenido en la lista. Imprime los valores financieros con el símbolo $ y separadores de miles. Usa formato Markdown."
        )
        
        response = model.generate_content(prompt)
        return html.Div([
            html.Strong("✨ Asistente IA (Gemini):"), 
            html.Br(),
            dcc.Markdown(response.text)
        ])
    except Exception as e:
        return dbc.Alert(f"Error al conectar con Gemini: {str(e)}", color="danger")

@app.callback(
    [Output('tarjetas_kpi', 'children'), Output('graf_lineas', 'figure'), Output('graf_barras', 'figure'), Output('graf_burbujas', 'figure'), Output('graf_top', 'figure')],
    [Input('filtro_fecha_inicio', 'value'), Input('filtro_fecha_fin', 'value'), Input('filtro_zona', 'value'), Input('filtro_metrica', 'value'), Input('filtro_anios_barras', 'value')]
)
def actualizar_dashboard(fecha_inicio, fecha_fin, zona_sel, tipo_m, num_anios):
    if not all([fecha_inicio, fecha_fin, zona_sel, tipo_m, num_anios]): raise dash.exceptions.PreventUpdate
    fecha_inicio_dt, fecha_fin_dt, num_anios = pd.to_datetime(fecha_inicio), pd.to_datetime(fecha_fin), int(num_anios)
    df_nac_filt = df_nac[df_nac['Fecha'] <= fecha_fin_dt]
    if not df_nac_filt.empty:
        ultima_fecha = df_nac_filt['Fecha'].max()
        res_kpi = df_nac[df_nac['Fecha'] == ultima_fecha].iloc[0] if zona_sel == "Nacional (Promedio)" else df_city[(df_city['Ciudad'] == zona_sel) & (df_city['Fecha'] == ultima_fecha)].iloc[0]
    else: res_kpi = None

    ac_con = res_kpi['Tot_City_Acum'] if res_kpi is not None else 0.0
    me_con = res_kpi['Tot_City_Men'] if res_kpi is not None else 0.0
    an_con = res_kpi['Tot_City_Anual'] if res_kpi is not None else 0.0
    fecha_con_str = ultima_fecha.strftime('%b %y') if not df_nac_filt.empty else "N/A"
    
    def get_ext_vals(df_e):
        df_h = df_e[df_e['Fecha_Align'] <= fecha_fin_dt]
        if not df_h.empty:
            r = df_h.sort_values('Fecha_Align', ascending=False).iloc[0] 
            return r['Acumulada'], r['Mensual'], r['Anual'], r['Fecha_Align'].strftime('%b %y')
        return 0.0, 0.0, 0.0, "N/A"

    c_ac, c_me, c_an, f_cam = get_ext_vals(df_camacol)
    i_ac, i_me, i_an, f_ico = get_ext_vals(df_icoced)
    p_ac, p_me, p_an, f_ipc = get_ext_vals(df_ipc)

    def crear_tarjeta(titulo, zona, ac, me, an, color, fd):
        c_flecha = '#e11d48' if me > 0.0001 else (C_VERDE if me < -0.0001 else '#64748B')
        flecha = "↑" if me > 0.0001 else ("↓" if me < -0.0001 else "−")
        return dbc.Col(dbc.Card(dbc.CardBody([
            html.Div([html.H6(titulo, style={'color': color, 'fontWeight': 'bold', 'margin': 0}), html.Small(fd, className="text-muted")], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}),
            html.Div(zona, style={'fontSize': '0.75rem', 'color': '#64748B', 'marginBottom': '5px'}),
            html.H3(f"{ac:+.2%}", style={'fontWeight': '900', 'margin': '0px', 'color': C_TEXTO, 'fontSize': '1.8rem'}),
            html.Div([
                html.Span(f"{flecha} {me:+.2%} Men", style={'color': c_flecha, 'fontWeight': 'bold', 'fontSize': '0.9rem'}),
                html.Span(f"YoY: {an:+.2%}", className="text-muted", style={'fontSize':'0.85rem', 'fontWeight': 'bold'})
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'borderTop': f'1px solid {C_GRIS}', 'paddingTop': '4px', 'marginTop': '4px'})
        ]), style={'borderLeft': f'6px solid {color}', 'boxShadow': '0 2px 5px rgba(0,0,0,0.04)', 'padding': '5px', 'borderRadius': '10px', 'border': 'none'}))

    tarjetas = [crear_tarjeta("Coninsa", zona_sel, ac_con, me_con, an_con, C_VERDE, fecha_con_str), crear_tarjeta("Camacol", "Referencia", c_ac, c_me, c_an, C_AZUL, f_cam), crear_tarjeta("ICOCED", "Referencia", i_ac, i_me, i_an, C_ROJO_ICOCED, f_ico), crear_tarjeta("IPC", "Referencia", p_ac, p_me, p_an, C_LIME, f_ipc)]

    col_t = 'Tot_City_Acum' if tipo_m == "Acumulada" else ('Tot_City_Men' if tipo_m == "Mensual" else 'Tot_City_Anual')
    col_e = 'Acumulada' if tipo_m == "Acumulada" else ('Mensual' if tipo_m == "Mensual" else 'Anual')

    df_nac_l = df_nac[(df_nac['Fecha'] >= fecha_inicio_dt) & (df_nac['Fecha'] <= fecha_fin_dt)].copy()
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=df_nac_l['Fecha'], y=df_nac_l[col_t], mode='lines+markers+text', name='Coninsa', text=df_nac_l[col_t], texttemplate='<b>%{text:+.2%}</b>', textposition='top center', textfont=dict(color=C_VERDE, size=11), line=dict(color=C_VERDE, width=3, shape='spline')))
    if not df_camacol.empty:
        df_cam_l = df_camacol[(df_camacol['Fecha_Align'] >= fecha_inicio_dt) & (df_camacol['Fecha_Align'] <= fecha_fin_dt)].sort_values('Fecha_Align')
        if not df_cam_l.empty: fig_line.add_trace(go.Scatter(x=df_cam_l['Fecha_Align'], y=df_cam_l[col_e], mode='lines+markers+text', name='Camacol', text=df_cam_l[col_e], texttemplate='<b>%{text:+.2%}</b>', textposition='top center', textfont=dict(color=C_AZUL, size=10), line=dict(color=C_AZUL, width=2)))
    if not df_icoced.empty:
        df_ico_l = df_icoced[(df_icoced['Fecha_Align'] >= fecha_inicio_dt) & (df_icoced['Fecha_Align'] <= fecha_fin_dt)].sort_values('Fecha_Align')
        if not df_ico_l.empty: fig_line.add_trace(go.Scatter(x=df_ico_l['Fecha_Align'], y=df_ico_l[col_e], mode='lines+markers+text', name='ICOCED', text=df_ico_l[col_e], texttemplate='<b>%{text:+.2%}</b>', textposition='bottom center', textfont=dict(color=C_ROJO_ICOCED, size=10), line=dict(color=C_ROJO_ICOCED, width=2)))
    if not df_reajuste.empty:
        df_rea_l = df_reajuste[(df_reajuste['Fecha_Align'] >= fecha_inicio_dt) & (df_reajuste['Fecha_Align'] <= fecha_fin_dt)].sort_values('Fecha_Align')
        if not df_rea_l.empty: fig_line.add_trace(go.Scatter(x=df_rea_l['Fecha_Align'], y=df_rea_l[col_e], mode='lines+markers+text', name='Coninsa-Reajuste', text=df_rea_l[col_e], texttemplate='<b>%{text:+.2%}</b>', textposition='bottom right', textfont=dict(color=C_AMARILLO_REA, size=10), line=dict(color=C_AMARILLO_REA, width=2, dash='dash')))
            
    fig_line.update_layout(title=f"<b>Tendencia: {tipo_m}</b>", template="plotly_white", margin=dict(l=20, r=20, t=45, b=20), yaxis=dict(tickformat='.1%'), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

    año_sel = fecha_fin_dt.year
    anios_hist = [str(año_sel - i) for i in range(num_anios)][::-1] if fecha_fin_dt.month == 12 else [str(año_sel - i) for i in range(1, num_anios + 1)][::-1]
    fig_bar = go.Figure()

    def get_cierre(df, col_fecha, col_valor, años_lista):
        valores = []
        if df.empty: return [0.0] * len(años_lista)
        for y in años_lista:
            df_y = df[df[col_fecha].dt.year == int(y)]
            if not df_y.empty:
                df_y_dec = df_y[df_y[col_fecha].dt.month == 12]
                valores.append(df_y_dec.sort_values(col_fecha).iloc[-1][col_valor] if not df_y_dec.empty else df_y.sort_values(col_fecha).iloc[-1][col_valor])
            else: valores.append(0.0)
        return valores

    vals_con = get_cierre(df_nac, 'Fecha', 'Tot_City_Acum', anios_hist)
    vals_cam = get_cierre(df_camacol, 'Fecha_Align', 'Acumulada', anios_hist)
    vals_ico = get_cierre(df_icoced, 'Fecha_Align', 'Acumulada', anios_hist)
    vals_ipc = get_cierre(df_ipc, 'Fecha_Align', 'Acumulada', anios_hist)

    def trazar_barra(fig, nombre, x_vals, y_vals, color):
        textos = [f"{v:+.2%}" if v != 0 else "" for v in y_vals]
        fig.add_trace(go.Bar(name=nombre, x=x_vals, y=y_vals, marker_color=color, text=textos, textposition='auto', texttemplate='<b>%{text}</b>'))

    trazar_barra(fig_bar, 'Coninsa', anios_hist, vals_con, C_VERDE)
    if not df_camacol.empty: trazar_barra(fig_bar, 'Camacol', anios_hist, vals_cam, C_AZUL)
    if not df_icoced.empty: trazar_barra(fig_bar, 'ICOCED', anios_hist, vals_ico, C_ROJO_ICOCED)
    if not df_ipc.empty: trazar_barra(fig_bar, 'IPC', anios_hist, vals_ipc, C_LIME)
    fig_bar.update_layout(title="<b>Cierres Anuales</b>", template="plotly_white", margin=dict(l=20, r=20, t=70, b=20), barmode='group', yaxis=dict(showticklabels=False))

    df_j_filt = df_j[df_j['Fecha'] <= fecha_fin_dt]
    fe_burb = df_j_filt['Fecha'].max() if not df_j_filt.empty else fecha_fin_dt
    df_b_base = df_j[df_j['Fecha'] == fe_burb] if zona_sel == "Nacional (Promedio)" else df_j[(df_j['Fecha'] == fe_burb) & (df_j['Ciudad'] == zona_sel)].copy()
    
    df_b_base['Peso_Promedio'] = (df_b_base['Peso_VIS'] + df_b_base['Peso_No_VIS']) / 2
    df_b_base['Inc_Men_Prom'] = df_b_base['Var_Cat_Men'] * df_b_base['Peso_Promedio']
    df_b_base['Inc_Acum_Prom'] = df_b_base['Var_Cat_Acum'] * df_b_base['Peso_Promedio']
    df_b_base['Inc_Anual_Prom'] = df_b_base['Var_Cat_Anual'] * df_b_base['Peso_Promedio']
    
    if tipo_m == "Mensual": col_var, col_inc = 'Var_Cat_Men', 'Inc_Men_Prom'
    elif tipo_m == "Acumulada": col_var, col_inc = 'Var_Cat_Acum', 'Inc_Acum_Prom'
    else: col_var, col_inc = 'Var_Cat_Anual', 'Inc_Anual_Prom'
        
    df_plot = df_b_base.groupby('Categoria', observed=True).agg({'Peso_Promedio': 'mean', col_inc: 'sum', col_var: 'mean'}).reset_index()
    umbral_bub = df_plot[col_var].abs().quantile(0.80)
    df_plot['Label'] = df_plot.apply(lambda r: r['Categoria'] if abs(r[col_var]) >= umbral_bub else "", axis=1)
    
    fig_bub = px.scatter(df_plot, x=col_inc, y='Peso_Promedio', size=df_plot[col_var].abs()+0.001, color='Categoria', text='Label', size_max=40)
    fig_bub.update_traces(textposition='top center')
    fig_bub.update_layout(title=f"<b>Matriz Incidencia vs Peso ({tipo_m})</b>", template="plotly_white", margin=dict(l=20, r=30, t=40, b=20), showlegend=False, xaxis_tickformat='.2%', yaxis_tickformat='.2%')

    df_plot_sorted = df_plot[df_plot[col_var] != 0].copy() 
    df_pos = df_plot_sorted[df_plot_sorted[col_var] > 0].sort_values(col_var, ascending=False).head(5)
    df_neg = df_plot_sorted[df_plot_sorted[col_var] < 0].sort_values(col_var, ascending=True).head(5)
    top_bot = pd.concat([df_neg, df_pos]).sort_values(col_var)
    if top_bot.empty: top_bot = pd.concat([df_plot.sort_values(col_var).head(5), df_plot.sort_values(col_var).tail(5)]).drop_duplicates()
    top_bot['Cat_Corta'] = top_bot['Categoria'].apply(lambda x: str(x)[:22] + '..' if len(str(x))>22 else str(x))
    
    fig_top = go.Figure(go.Bar(x=top_bot[col_var], y=top_bot['Cat_Corta'], orientation='h', marker_color=[C_VERDE if x < 0 else '#e11d48' for x in top_bot[col_var]], text=top_bot[col_var], texttemplate='<b>%{text:+.2%}</b>', textposition='auto'))
    fig_top.update_layout(title=f"<b>Top Ítems ({tipo_m})</b>", template="plotly_white", margin=dict(l=10, r=40, t=40, b=20), xaxis=dict(showticklabels=False))

    return tarjetas, fig_line, fig_bar, fig_bub, fig_top

@app.callback(
    Output('graf_comparativo_barras_agrupadas', 'figure'),
    [Input('filtro_fecha_fin', 'value'), Input('filtro_zona_comp', 'value'), Input('filtro_categoria_interna', 'value')]
)
def generar_grafico_comparativo_agrupado(fecha_sel, zona_sel, cats_sel):
    if not fecha_sel or df_h_cat.empty: return go.Figure()
    fecha_dt = pd.to_datetime(fecha_sel)
    df_j_filt = df_j[df_j['Fecha'] <= fecha_dt]
    fecha_efectiva = df_j_filt['Fecha'].max() if not df_j_filt.empty else fecha_dt
    
    df_b = df_j[df_j['Fecha'] == fecha_efectiva].copy()
    if zona_sel and zona_sel != "Nacional (Promedio)": df_b = df_b[df_b['Ciudad'] == zona_sel]
    df_b['Cat_Clean'] = df_b['Categoria'].apply(limpiar_texto)
    dict_con = df_b.groupby('Cat_Clean', observed=True)['Var_Cat_Acum'].mean().to_dict()
    
    df_e = df_ext[pd.to_datetime(df_ext['Fecha_Align']) <= fecha_dt].sort_values('Fecha_Align').groupby(['Fuente_Up', 'Cat_Up'], observed=True).tail(1)
    df_e['Cat_Clean'] = df_e['Cat_Up'].apply(limpiar_texto)
    dict_cam = df_e[df_e['Fuente_Up'].astype(str).str.contains('CAMACOL', case=False, na=False)].set_index('Cat_Clean')['Acumulada'].to_dict()
    dict_ico = df_e[df_e['Fuente_Up'].astype(str).str.contains('ICOCED', case=False, na=False)].set_index('Cat_Clean')['Acumulada'].to_dict()
    
    col_con, col_cam, col_ico = df_h_cat.columns[0], df_h_cat.columns[1], df_h_cat.columns[2]
    df_h_cat_filtered = df_h_cat[df_h_cat[col_con].isin(cats_sel)] if cats_sel else df_h_cat
    
    datos_grafico = []
    for _, row in df_h_cat_filtered.iterrows():
        val_con = dict_con.get(limpiar_texto(row[col_con]), 0.0)
        val_cam = dict_cam.get(limpiar_texto(row[col_cam]), 0.0)
        val_ico = dict_ico.get(limpiar_texto(row[col_ico]), 0.0)
        nombre = '<br>'.join(textwrap.wrap(str(row[col_con]).title(), width=18))
        datos_grafico.append({'Categoria': nombre, 'Coninsa': val_con, 'Camacol': val_cam, 'Icoced': val_ico, 'Filtro': val_con})
        
    df_final = pd.DataFrame(datos_grafico).sort_values('Filtro', ascending=False)
    if df_final.empty: return go.Figure()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Coninsa', x=df_final['Categoria'], y=df_final['Coninsa'], marker_color=C_VERDE, text=df_final['Coninsa'], texttemplate='<b>%{text:+.2%}</b>', textposition='auto'))
    fig.add_trace(go.Bar(name='Camacol', x=df_final['Categoria'], y=df_final['Camacol'], marker_color=C_AZUL, text=df_final['Camacol'], texttemplate='<b>%{text:+.2%}</b>', textposition='auto'))
    fig.add_trace(go.Bar(name='Icoced', x=df_final['Categoria'], y=df_final['Icoced'], marker_color=C_ROJO_ICOCED, text=df_final['Icoced'], texttemplate='<b>%{text:+.2%}</b>', textposition='auto'))
    fig.update_layout(template="plotly_white", margin=dict(l=40, r=40, t=60, b=150), barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), yaxis=dict(tickformat='.0%'))
    return fig

@app.callback(
    [Output('graf_insumo_precio', 'figure'), Output('graf_insumo_variacion', 'figure')],
    [Input('filtro_insumo_detalle', 'value'), Input('filtro_zona_insumo', 'value'), Input('filtro_fecha_inicio', 'value'), Input('filtro_fecha_fin', 'value')]
)
def actualizar_analisis_insumo(insumo_sel, zona_sel, fecha_inicio, fecha_fin):
    # OPTIMIZACIÓN: Carga Perezosa (Solo llama las matemáticas pesadas cuando vas a la Pestaña 5)
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import PolynomialFeatures
    from sklearn.pipeline import make_pipeline

    if not all([insumo_sel, fecha_inicio, fecha_fin]): raise dash.exceptions.PreventUpdate
    fini, ffin = pd.to_datetime(fecha_inicio), pd.to_datetime(fecha_fin)
    df_r = df_m[(df_m['Fecha'] >= fini) & (df_m['Fecha'] <= ffin)]

    if zona_sel == "Nacional (Promedio)":
        df_i = df_r[df_r['Nombre_Insumo'] == insumo_sel].groupby('Fecha', observed=True).mean(numeric_only=True).reset_index()
        cat_insumo = df_r[df_r['Nombre_Insumo'] == insumo_sel]['Categoria'].iloc[0] if not df_r[df_r['Nombre_Insumo'] == insumo_sel].empty else None
    else:
        df_i = df_r[(df_r['Nombre_Insumo'] == insumo_sel) & (df_r['Ciudad'] == zona_sel)].copy()
        cat_insumo = df_i['Categoria'].iloc[0] if not df_i.empty else None

    if df_i.empty: return go.Figure(), go.Figure()

    fig_precio = go.Figure()
    fig_precio.add_trace(go.Scatter(x=df_i['Fecha'], y=df_i['Valor_Unitario'], mode='lines+markers+text', name='Real', line=dict(color='#64748B', width=3), text=df_i['Valor_Unitario'], textposition='top center', texttemplate='$%{text:,.0f}'))

    df_train = df_m[df_m['Fecha'] <= ffin].copy()
    if zona_sel == "Nacional (Promedio)": df_train = df_train[df_train['Nombre_Insumo'] == insumo_sel].groupby('Fecha', observed=True).mean(numeric_only=True).reset_index()
    else: df_train = df_train[(df_train['Nombre_Insumo'] == insumo_sel) & (df_train['Ciudad'] == zona_sel)].copy()
    df_train = df_train.dropna(subset=['Valor_Unitario']).sort_values('Fecha')
    
    if len(df_train) >= 6: 
        df_train['Fecha_Ordinal'] = df_train['Fecha'].astype('int64') // 10**9
        X_train, y_train = df_train[['Fecha_Ordinal']], df_train['Valor_Unitario']
        modelo_ia = make_pipeline(PolynomialFeatures(degree=2), Ridge())
        modelo_ia.fit(X_train, y_train)

        ultima_fecha = df_train['Fecha'].max()
        fin_de_ano = pd.to_datetime(f"{ultima_fecha.year}-12-01")
        if ultima_fecha < fin_de_ano:
            fechas_futuras = pd.date_range(start=ultima_fecha + pd.DateOffset(months=1), end=fin_de_ano, freq='MS')
            prediccion = np.maximum(modelo_ia.predict(pd.DataFrame({'Fecha_Ordinal': fechas_futuras.astype('int64') // 10**9})), 0)
            plot_f, plot_p, txt_p = [ultima_fecha] + list(fechas_futuras), [y_train.iloc[-1]] + list(prediccion), [""] + list(prediccion)
            fig_precio.add_trace(go.Scatter(x=plot_f, y=plot_p, mode='lines+markers+text', name='Proyección IA', line=dict(color=C_TEAL, width=3, dash='dash'), text=txt_p, textposition='top center', texttemplate='$%{text:,.0f}'))
            fig_precio.update_layout(xaxis=dict(range=[fini, fin_de_ano + pd.DateOffset(days=15)]))

    fig_precio.update_layout(title=f"<b>Precios y Proyección: {str(insumo_sel).title()}</b>", template="plotly_white", yaxis=dict(tickformat='$,.0f'))

    fig_var = go.Figure()
    fig_var.add_trace(go.Scatter(x=df_i['Fecha'], y=df_i['Var_Acum_Ins'], mode='lines+markers+text', name='CONINSA', line=dict(color=C_VERDE, width=3), text=df_i['Var_Acum_Ins'], textposition='top center', texttemplate='%{text:+.2%}'))

    if cat_insumo and not df_h_cat.empty:
        col_con, col_cam, col_ico = df_h_cat.columns[0], df_h_cat.columns[1], df_h_cat.columns[2]
        row_h = df_h_cat[df_h_cat[col_con].astype(str).str.strip().str.upper() == limpiar_texto(cat_insumo)]
        if not row_h.empty:
            cat_cam_key, cat_ico_key = limpiar_texto(row_h.iloc[0][col_cam]), limpiar_texto(row_h.iloc[0][col_ico])
            df_e = df_ext[(df_ext['Fecha_Align'] >= fini) & (df_ext['Fecha_Align'] <= ffin)].copy()
            df_e['Cat_Clean'] = df_e['Cat_Up'].apply(limpiar_texto)
            df_cam = df_e[(df_e['Fuente_Up'].astype(str).str.contains('CAMACOL', case=False, na=False)) & (df_e['Cat_Clean'] == cat_cam_key)].sort_values('Fecha_Align')
            if not df_cam.empty: fig_var.add_trace(go.Scatter(x=df_cam['Fecha_Align'], y=df_cam['Acumulada'], mode='lines+markers+text', name='CAMACOL', line=dict(color=C_AZUL, width=2), text=df_cam['Acumulada'], textposition='bottom center', texttemplate='%{text:+.2%}'))
            df_ico = df_e[(df_e['Fuente_Up'].astype(str).str.contains('ICOCED', case=False, na=False)) & (df_e['Cat_Clean'] == cat_ico_key)].sort_values('Fecha_Align')
            if not df_ico.empty: fig_var.add_trace(go.Scatter(x=df_ico['Fecha_Align'], y=df_ico['Acumulada'], mode='lines+markers+text', name='ICOCED', line=dict(color=C_ROJO_ICOCED, width=2), text=df_ico['Acumulada'], textposition='bottom right', texttemplate='%{text:+.2%}'))

    fig_var.update_layout(title="<b>% Variación Acumulada</b>", template="plotly_white", yaxis=dict(tickformat='.1%'), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
    return fig_precio, fig_var

@app.callback(
    Output('tbl_incidencias_auditoria', 'children'),
    [Input('filtro_fecha_fin', 'value')]
)
def update_incidencias_auditoria(fs):
    if not fs or df_j.empty: return html.Div()
    dt = pd.to_datetime(fs)
    df_f = df_j[df_j['Fecha'] <= dt].copy()
    if df_f.empty: return html.Div()
    
    fe = df_f['Fecha'].max()
    df_b = df_f[df_f['Fecha'] == fe].copy()
    
    df_b['Peso_Promedio'] = (df_b['Peso_VIS'] + df_b['Peso_No_VIS']) / 2
    df_b['Incidencia_Men'] = df_b['Var_Cat_Men'] * df_b['Peso_Promedio']
    df_b['Incidencia_Acum'] = df_b['Var_Cat_Acum'] * df_b['Peso_Promedio']
    df_b['Incidencia_YoY'] = df_b['Var_Cat_Anual'] * df_b['Peso_Promedio']
    
    df_show = df_b[['Ciudad', 'Categoria', 'Peso_Promedio', 'Var_Cat_Men', 'Incidencia_Men', 'Var_Cat_Acum', 'Incidencia_Acum', 'Var_Cat_Anual', 'Incidencia_YoY']].copy()
    
    fmt_p = Format(scheme=Scheme.percentage, precision=4)
    cols = [{'name': str(c), 'id': str(c)} if c in ['Ciudad', 'Categoria'] else {'name': str(c), 'id': str(c), 'type': 'numeric', 'format': fmt_p} for c in df_show.columns]
    
    return dash_table.DataTable(
        data=df_show.to_dict('records'), columns=cols,
        style_header={'backgroundColor': C_AZUL, 'color': 'white', 'fontWeight': 'bold', 'textAlign': 'center'},
        style_cell={'textAlign': 'center', 'padding': '5px', 'fontSize': '11px', 'minWidth': '80px'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8FAFC'}],
        filter_action='native', sort_action='native',
        export_format='xlsx', export_headers='display',
        page_size=20
    )

@app.callback(
    [Output('b100_filtro1', 'options'), Output('b100_filtro1', 'value'), Output('b100_filtro1', 'disabled'), Output('b100_filtro2', 'options'), Output('b100_filtro2', 'value'), Output('b100_filtro2', 'disabled')],
    [Input('b100_nivel', 'value')]
)
def update_b100_dropdowns(nivel):
    opts_ciudad = [{'label': c, 'value': c} for c in zonas_disp if c != 'Nacional (Promedio)']
    if nivel == 'nac':
        return [], None, True, [], None, True
    elif nivel == 'city':
        return opts_ciudad, opts_ciudad[0]['value'] if opts_ciudad else None, False, [], None, True
    elif nivel == 'cat':
        opts_cat = [{'label': str(c), 'value': str(c)} for c in df_b100_cat['Categoria'].dropna().unique()]
        return opts_ciudad, opts_ciudad[0]['value'] if opts_ciudad else None, False, opts_cat, opts_cat[0]['value'] if opts_cat else None, False
    elif nivel == 'ins':
        opts_ins = [{'label': str(i), 'value': str(i)} for i in insumos_disp]
        return opts_ciudad, opts_ciudad[0]['value'] if opts_ciudad else None, False, opts_ins, opts_ins[0]['value'] if opts_ins else None, False
    return [], None, True, [], None, True

@app.callback(
    Output('graf_base100', 'figure'),
    [Input('b100_nivel', 'value'), Input('b100_filtro1', 'value'), Input('b100_filtro2', 'value')]
)
def update_b100_graph(nivel, f1, f2):
    fig = go.Figure()
    df_plot = pd.DataFrame()
    
    if nivel == 'nac': df_plot = df_b100_nac.copy()
    elif nivel == 'city' and f1: df_plot = df_b100_city[df_b100_city['Ciudad'] == f1].copy()
    elif nivel == 'cat' and f1 and f2: df_plot = df_b100_cat[(df_b100_cat['Ciudad'] == f1) & (df_b100_cat['Categoria'] == f2)].copy()
    elif nivel == 'ins' and f1 and f2: df_plot = df_b100_ins[(df_b100_ins['Ciudad'] == f1) & (df_b100_ins['Nombre_Insumo'] == f2)].copy()
    
    if not df_plot.empty:
        nom = 'Nacional' if nivel == 'nac' else (f1 if nivel == 'city' else f"{f2} ({f1})")
        col = 'Base100_Nac' if nivel == 'nac' else ('Base100_City' if nivel == 'city' else ('Base100_Cat' if nivel == 'cat' else 'Base100_Ins'))
        fig.add_trace(go.Scatter(x=df_plot['Fecha'], y=df_plot[col], mode='lines+markers+text', name=nom, line=dict(color=C_VERDE, width=3), text=df_plot[col], texttemplate='<b>%{text:.1f}</b>', textposition='top center'))
        
    fig.update_layout(title="<b>Evolución Índice Base 100</b>", template="plotly_white", margin=dict(l=20, r=20, t=40, b=20), yaxis=dict(title='Índice Base 100'), xaxis=dict(title='Fecha'))
    return fig

@app.callback(
    [Output('tbl_b100_nac', 'children'), Output('tbl_b100_city', 'children'), Output('tbl_b100_cat', 'children'), Output('tbl_b100_ins', 'children')],
    [Input('filtro_fecha_fin', 'value')]
)
def update_b100_tables(fs):
    if df_b100_nac.empty: return html.Div(), html.Div(), html.Div(), html.Div()
    
    fmt = Format(scheme=Scheme.fixed, precision=2)
    def make_tbl(df_t, idx_cols, val_col):
        df_copy = df_t.copy()
        df_copy['Fecha_Str'] = df_copy['Fecha'].dt.strftime('%Y-%m')
        piv = df_copy.pivot_table(index=idx_cols, columns='Fecha_Str', values=val_col, aggfunc='first', observed=True).reset_index()
        
        cols = [{'name': str(c), 'id': str(c)} if c in idx_cols else {'name': str(c), 'id': str(c), 'type': 'numeric', 'format': fmt} for c in piv.columns]
        return dash_table.DataTable(
            data=piv.to_dict('records'), columns=cols,
            style_header={'backgroundColor': C_AZUL, 'color': 'white', 'fontWeight': 'bold', 'textAlign': 'center'},
            style_cell={'textAlign': 'center', 'padding': '5px', 'fontSize': '11px', 'minWidth': '90px'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8FAFC'}],
            style_table={'overflowX': 'auto'},
            export_format='xlsx', export_headers='display', page_size=15, sort_action='native', filter_action='native'
        )
        
    tbl_nac = make_tbl(df_b100_nac, ['Fecha_Str'], 'Base100_Nac') if 'Fecha_Str' in df_b100_nac.columns else make_tbl(df_b100_nac, ['Fecha'], 'Base100_Nac')
    tbl_city = make_tbl(df_b100_city, ['Ciudad'], 'Base100_City')
    tbl_cat = make_tbl(df_b100_cat, ['Ciudad', 'Categoria'], 'Base100_Cat')
    tbl_ins = make_tbl(df_b100_ins, ['Ciudad', 'Categoria', 'Nombre_Insumo'], 'Base100_Ins')
    
    return tbl_nac, tbl_city, tbl_cat, tbl_ins

if __name__ == '__main__':
    app.run(debug=True, port=8050)
