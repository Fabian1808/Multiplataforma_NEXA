import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Dashboard Asistencia", page_icon="??", layout="wide")

# Styling corporativo
st.markdown("""
<style>
    .reportview-container {
        background: #F8F9FA;
    }
    .main .block-container {
        padding-top: 2rem;
    }
    .kpi-card {
        background-color: white;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        border-left: 5px solid #FF5A00;
    }
    .kpi-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1F2937;
    }
    .kpi-label {
        font-size: 1rem;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

st.title("?? Dashboard Ejecutivo: Asistencia Masiva")

@st.cache_data(ttl=60)
def load_data():
    base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    db_path = base_dir / "historico" / "asistencia" / "db.csv"
    if not db_path.exists():
        return None
    df = pd.read_csv(db_path)
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"])
    return df

df = load_data()

if df is None or df.empty:
    st.warning("No hay datos de asistencia procesados aún. Ejecuta 'Asistencia Masiva' primero.")
    st.stop()

# ================= SIDEBAR =================
st.sidebar.header("Filtros")
min_date = df["Fecha"].min()
max_date = df["Fecha"].min() if df.empty else df["Fecha"].max()
date_range = st.sidebar.date_input("Rango de Fechas", [min_date, max_date], min_value=min_date, max_value=max_date)

empresas = ["Todas"] + list(df["Empresa"].dropna().unique())
sel_empresa = st.sidebar.selectbox("Empresa / Contratista", empresas)

empleados = df["Empleado"].dropna().unique()
sel_empleados = st.sidebar.multiselect("Empleados", empleados)

# ================= FILTRADO =================
df_filtered = df.copy()
if len(date_range) == 2:
    start_date, end_date = date_range
    df_filtered = df_filtered[(df_filtered["Fecha"].dt.date >= start_date) & (df_filtered["Fecha"].dt.date <= end_date)]

if sel_empresa != "Todas":
    df_filtered = df_filtered[df_filtered["Empresa"] == sel_empresa]

if sel_empleados:
    df_filtered = df_filtered[df_filtered["Empleado"].isin(sel_empleados)]

if df_filtered.empty:
    st.error("No hay datos para los filtros seleccionados.")
    st.stop()

# ================= KPIs =================
total_personal = df_filtered["Empleado"].nunique()
total_horas = df_filtered["Horas Trabajadas Hexagesimales"].sum()
promedio_horas = total_horas / total_personal if total_personal > 0 else 0
dias_registrados = df_filtered["Fecha"].nunique()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-label">Total Personal</div><div class="kpi-value">{total_personal}</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="kpi-card"><div class="kpi-label">Horas Totales</div><div class="kpi-value">{total_horas:,.1f}</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="kpi-card"><div class="kpi-label">Productividad (Hrs/Persona)</div><div class="kpi-value">{promedio_horas:,.1f}</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="kpi-card"><div class="kpi-label">Días Registrados</div><div class="kpi-value">{dias_registrados}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ================= GRÁFICOS =================
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("?? Evolución de Horas Trabajadas")
    df_trend = df_filtered.groupby("Fecha")["Horas Trabajadas Hexagesimales"].sum().reset_index()
    fig1 = px.area(df_trend, x="Fecha", y="Horas Trabajadas Hexagesimales", 
                  color_discrete_sequence=["#FF5A00"],
                  template="plotly_white")
    st.plotly_chart(fig1, use_container_width=True)

with c2:
    st.subheader("?? Distribución por Empresa")
    df_emp = df_filtered.groupby("Empresa")["Horas Trabajadas Hexagesimales"].sum().reset_index()
    fig2 = px.pie(df_emp, values="Horas Trabajadas Hexagesimales", names="Empresa", hole=0.4,
                  color_discrete_sequence=px.colors.sequential.Oranges_r)
    st.plotly_chart(fig2, use_container_width=True)


c3, c4 = st.columns(2)

with c3:
    st.subheader("?? Top 10 Empleados (Horas)")
    df_top = df_filtered.groupby("Empleado")["Horas Trabajadas Hexagesimales"].sum().reset_index()
    df_top = df_top.sort_values("Horas Trabajadas Hexagesimales", ascending=False).head(10)
    fig3 = px.bar(df_top, x="Horas Trabajadas Hexagesimales", y="Empleado", orientation='h',
                  color="Horas Trabajadas Hexagesimales", color_continuous_scale="Oranges",
                  template="plotly_white")
    fig3.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig3, use_container_width=True)

with c4:
    st.subheader("?? Heatmap de Productividad (Día de la semana)")
    df_filtered["DiaSemana"] = df_filtered["Fecha"].dt.day_name()
    df_heat = df_filtered.groupby("DiaSemana")["Horas Trabajadas Hexagesimales"].sum().reset_index()
    # Orden correcto
    dias_orden = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    df_heat["DiaSemana"] = pd.Categorical(df_heat["DiaSemana"], categories=dias_orden, ordered=True)
    df_heat = df_heat.sort_values("DiaSemana")
    fig4 = px.bar(df_heat, x="DiaSemana", y="Horas Trabajadas Hexagesimales",
                  color="Horas Trabajadas Hexagesimales", color_continuous_scale="Oranges",
                  template="plotly_white")
    st.plotly_chart(fig4, use_container_width=True)

# ================= TABLA DETALLE =================
st.subheader("?? Detalle de Registros")
st.dataframe(df_filtered, use_container_width=True)
