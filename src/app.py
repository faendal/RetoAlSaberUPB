import io
import sys
import pandas as pd
import streamlit as st
from pathlib import Path
import plotly.express as px

# Asegurar acceso a módulos dentro de src/
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from etl import PROCESSED_DIR, ejecutar_etl

st.set_page_config(
    page_title="Resultados Saber & Autodiagnóstica",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2rem;
    }
    div[data-testid="metric-container"] {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #1E3A8A;
        padding: 14px 18px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(15, 23, 42, 0.04);
    }
    div[data-testid="metric-container"] label {
        color: #475569;
        font-weight: 600;
        font-size: 0.85rem;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #0F172A;
        font-weight: 700;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def cargar_datos(ruta_reto: Path, ruta_auto: Path):
    df_r = pd.read_excel(ruta_reto)
    df_a = pd.read_excel(ruta_auto)

    df_r.columns = df_r.columns.str.strip()
    df_a.columns = df_a.columns.str.strip()

    df_r["Estado"] = df_r["Estado"].astype(str).str.strip().str.title()
    df_a["Estado"] = df_a["Estado"].astype(str).str.strip().str.title()
    return df_r, df_a


def convertir_excel(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()


ruta_reto = PROCESSED_DIR / "REPORTE_FINAL_RETO_SABER.xlsx"
ruta_auto = PROCESSED_DIR / "REPORTE_FINAL_AUTODIAGNOSTICA.xlsx"

# Barra lateral de control
with st.sidebar:
    st.header("Gestión de Datos")
    st.caption(f"Leyendo desde: `data/processed/`")

    if st.button("Procesar archivos de /data/raw/", width='stretch'):
        with st.spinner("Ejecutando pipeline ETL..."):
            try:
                ejecutar_etl()
                st.cache_data.clear()
                st.success("Datos actualizados correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"Error en ETL: {e}")

# Si aún no existen los archivos procesados, ejecutar ETL automáticamente la primera vez
if not ruta_reto.exists() or not ruta_auto.exists():
    try:
        ejecutar_etl()
    except FileNotFoundError as e:
        st.error(f"Faltan archivos de origen: {e}")
        st.stop()

df_reto, df_auto = cargar_datos(ruta_reto, ruta_auto)

COLORES_Estado = {"Aprobado": "#10B981", "No Aprobado": "#EF4444"}

st.title("Panel de Seguimiento Académico")
st.markdown(
    "Consolidado histórico de desempeño en **Reto al Saber** y **Prueba Autodiagnóstica**."
)

tab1, tab2 = st.tabs(["Reto al Saber", "Prueba Autodiagnóstica"])

# ==============================================================================
# PESTAÑA 1: RETO AL SABER
# ==============================================================================
with tab1:
    with st.expander("Filtros de búsqueda", expanded=True):
        f1, f2, f3 = st.columns([1, 1, 2])
        with f1:
            sel_Estado_r = st.multiselect(
                "Estado:",
                options=df_reto["Estado"].unique(),
                default=df_reto["Estado"].unique(),
                key="est_r",
            )
        with f2:
            sel_cursos_r = st.multiselect(
                "Cursos Ganados:",
                options=sorted(df_reto["Cursos Ganados"].unique()),
                default=sorted(df_reto["Cursos Ganados"].unique()),
                key="cur_r",
            )
        with f3:
            txt_busqueda_r = st.text_input(
                "Buscar estudiante (Nombre o ID):",
                placeholder="Ej. 102030 o María...",
                key="bus_r",
            )

    dff_r = df_reto[
        (df_reto["Estado"].isin(sel_Estado_r))
        & (df_reto["Cursos Ganados"].isin(sel_cursos_r))
    ]
    if txt_busqueda_r.strip():
        q = txt_busqueda_r.strip()
        dff_r = dff_r[
            dff_r["Nombre"].astype(str).str.contains(q, case=False, na=False)
            | dff_r["Id"].astype(str).str.contains(q, case=False, na=False)
        ]

    if dff_r.empty:
        st.warning("No hay registros que coincidan con los filtros seleccionados.")
    else:
        total_r = len(dff_r)
        aprob_r = (dff_r["Estado"] == "Aprobado").sum()
        tasa_r = (aprob_r / total_r) * 100
        prom_cursos_r = dff_r["Cursos Ganados"].mean()

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Estudiantes", f"{total_r:,}")
        k2.metric("Aprobados (≥ 2 cursos)", f"{aprob_r:,}")
        k3.metric("Tasa de Aprobación", f"{tasa_r:.1f}%")
        k4.metric("Promedio Cursos Ganados", f"{prom_cursos_r:.2f} / 3")

        st.markdown("---")

        c1, c2 = st.columns(2)
        with c1:
            fig_pie_r = px.pie(
                dff_r,
                names="Estado",
                title="Proporción Global de Aprobación",
                hole=0.55,
                color="Estado",
                color_discrete_map=COLORES_Estado,
            )
            fig_pie_r.update_traces(textinfo="percent+value", textfont_size=13)
            fig_pie_r.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=50, b=20, l=20, r=20)
            )
            st.plotly_chart(fig_pie_r, width='stretch')

        with c2:
            dist_c = (
                dff_r["Cursos Ganados"]
                .value_counts()
                .reindex([0, 1, 2, 3], fill_value=0)
                .reset_index()
            )
            dist_c.columns = ["Cursos Ganados", "Estudiantes"]
            dist_c["Etiqueta"] = dist_c["Cursos Ganados"].astype(str) + " cursos"

            fig_bar_c = px.bar(
                dist_c,
                x="Etiqueta",
                y="Estudiantes",
                text="Estudiantes",
                title="Estudiantes según Cantidad de Cursos Ganados",
                color="Cursos Ganados",
                color_discrete_sequence=["#EF4444", "#F59E0B", "#3B82F6", "#10B981"],
            )
            fig_bar_c.update_traces(textposition="outside")
            fig_bar_c.update_layout(
                showlegend=False,
                xaxis_title="",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=50, b=20, l=20, r=20),
            )
            st.plotly_chart(fig_bar_c, width='stretch')

        c3, c4 = st.columns(2)
        modulos = [
            "Lectura Crítica",
            "Razonamiento Cuantitativo",
            "Competencias Ciudadanas",
        ]

        with c3:
            df_proms = pd.DataFrame(
                {
                    "Módulo": modulos,
                    "Nota Promedio": [dff_r[f"Nota {m}"].mean() for m in modulos],
                }
            )
            fig_mod = px.bar(
                df_proms,
                x="Nota Promedio",
                y="Módulo",
                orientation="h",
                text=df_proms["Nota Promedio"].round(2),
                title="Nota Histórica Promedio por Módulo (Meta > 3.0)",
                color_discrete_sequence=["#1E3A8A"],
            )
            fig_mod.add_vline(
                x=3.0,
                line_dash="dash",
                line_color="#EF4444",
                annotation_text="Mínimo (3.0)",
            )
            fig_mod.update_traces(textposition="outside")
            fig_mod.update_layout(
                xaxis_range=[0, 5.4],
                yaxis_title="",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=50, b=20, l=20, r=20),
            )
            st.plotly_chart(fig_mod, width='stretch')

        with c4:
            df_int_mod = pd.DataFrame(
                {
                    "Módulo": modulos,
                    "Intentos Promedio": [
                        dff_r[f"Intentos {m}"].mean() for m in modulos
                    ],
                }
            )
            fig_int_m = px.bar(
                df_int_mod,
                x="Módulo",
                y="Intentos Promedio",
                text=df_int_mod["Intentos Promedio"].round(2),
                title="Promedio de Intentos por Módulo",
                color="Módulo",
                color_discrete_sequence=["#0284C7", "#0D9488", "#6366F1"],
            )
            fig_int_m.update_traces(textposition="outside")
            fig_int_m.update_layout(
                showlegend=False,
                xaxis_title="",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=50, b=20, l=20, r=20),
            )
            st.plotly_chart(fig_int_m, width='stretch')

        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            st.subheader("Detalle de Estudiantes")
        with col_t2:
            st.download_button(
                label="Descargar tabla filtrada (.xlsx)",
                data=convertir_excel(dff_r),
                file_name="Reto_Saber_Filtrado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.dataframe(
            dff_r,
            width='stretch',
            hide_index=True,
            column_config={
                "Nota Lectura Crítica": st.column_config.ProgressColumn(
                    "Nota Lectura", format="%.2f", min_value=0, max_value=5
                ),
                "Nota Razonamiento Cuantitativo": st.column_config.ProgressColumn(
                    "Nota Razonamiento", format="%.2f", min_value=0, max_value=5
                ),
                "Nota Competencias Ciudadanas": st.column_config.ProgressColumn(
                    "Nota Competencias", format="%.2f", min_value=0, max_value=5
                ),
            },
        )

# ==============================================================================
# PESTAÑA 2: PRUEBA AUTODIAGNÓSTICA
# ==============================================================================
with tab2:
    with st.expander("Filtros de búsqueda", expanded=True):
        a1, a2, a3 = st.columns([1, 1, 2])
        with a1:
            sel_Estado_a = st.multiselect(
                "Estado:",
                options=df_auto["Estado"].unique(),
                default=df_auto["Estado"].unique(),
                key="est_a",
            )
        with a2:
            min_i, max_i = int(df_auto["Intentos"].min()), int(
                df_auto["Intentos"].max()
            )
            if min_i < max_i:
                rango_i = st.slider(
                    "Cantidad de Intentos:", min_i, max_i, (min_i, max_i), key="int_a"
                )
            else:
                rango_i = (min_i, max_i)
        with a3:
            txt_busqueda_a = st.text_input(
                "Buscar estudiante (Nombre o ID):",
                placeholder="Ej. 102030 o Carlos...",
                key="bus_a",
            )

    dff_a = df_auto[
        (df_auto["Estado"].isin(sel_Estado_a))
        & (df_auto["Intentos"].between(rango_i[0], rango_i[1]))
    ]
    if txt_busqueda_a.strip():
        q = txt_busqueda_a.strip()
        dff_a = dff_a[
            dff_a["Nombre"].astype(str).str.contains(q, case=False, na=False)
            | dff_a["Id"].astype(str).str.contains(q, case=False, na=False)
        ]

    if dff_a.empty:
        st.warning("No hay registros que coincidan con los filtros seleccionados.")
    else:
        total_a = len(dff_a)
        aprob_a = (dff_a["Estado"] == "Aprobado").sum()
        tasa_a = (aprob_a / total_a) * 100
        prom_pts_a = dff_a["Puntaje_Max"].mean()
        prom_int_a = dff_a["Intentos"].mean()

        ka1, ka2, ka3, ka4 = st.columns(4)
        ka1.metric("Total Estudiantes", f"{total_a:,}")
        ka2.metric("Aprobados (> 4.0)", f"{aprob_a:,}")
        ka3.metric("Tasa de Aprobación", f"{tasa_a:.1f}%")
        ka4.metric(
            "Puntaje / Intentos Prom.", f"{prom_pts_a:.2f} pts | {prom_int_a:.1f} int."
        )

        st.markdown("---")

        ga1, ga2 = st.columns(2)
        with ga1:
            fig_pie_a = px.pie(
                dff_a,
                names="Estado",
                title="Proporción de Aprobación - Autodiagnóstica",
                hole=0.55,
                color="Estado",
                color_discrete_map=COLORES_Estado,
            )
            fig_pie_a.update_traces(textinfo="percent+value", textfont_size=13)
            fig_pie_a.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=50, b=20, l=20, r=20)
            )
            st.plotly_chart(fig_pie_a, width='stretch')

        with ga2:
            grp_a = (
                dff_a.groupby(["Intentos", "Estado"])
                .size()
                .reset_index(name="Estudiantes")
            )
            fig_bar_a = px.bar(
                grp_a,
                x="Intentos",
                y="Estudiantes",
                color="Estado",
                barmode="group",
                text="Estudiantes",
                title="Esfuerzo vs. Éxito (Estudiantes por Número de Intentos)",
                color_discrete_map=COLORES_Estado,
            )
            fig_bar_a.update_xaxes(type="category")
            fig_bar_a.update_traces(textposition="outside")
            fig_bar_a.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=50, b=20, l=20, r=20),
            )
            st.plotly_chart(fig_bar_a, width='stretch')

        col_ta1, col_ta2 = st.columns([3, 1])
        with col_ta1:
            st.subheader("Detalle de Intentos y Puntaje Máximo")
        with col_ta2:
            st.download_button(
                label="Descargar tabla filtrada (.xlsx)",
                data=convertir_excel(dff_a),
                file_name="Autodiagnostica_Filtrada.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.dataframe(
            dff_a.sort_values(by=["Intentos", "Puntaje_Max"], ascending=[False, False]),
            width='stretch',
            hide_index=True,
            column_config={
                "Puntaje_Max": st.column_config.ProgressColumn(
                    "Puntaje Máximo", format="%.2f", min_value=0, max_value=5
                )
            },
        )
