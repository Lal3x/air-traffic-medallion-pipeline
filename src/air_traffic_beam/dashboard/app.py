"""Dashboard Streamlit da visão Gold e da saúde operacional do pipeline.

O app lê o snapshot Gold mais recente e usa DuckDB apenas como fallback para
consultar Parquets Silver. A interface não executa Beam: ela apresenta os
artefatos produzidos pelo processamento e os relatórios de observabilidade.
"""

from __future__ import annotations

import json
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import pandas as pd
import streamlit as st

SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")

DATA_DIR = Path(__file__).resolve().parents[3]


EMPTY_COLUMNS = [
    "icao24",
    "callsign",
    "origin_country",
    "latitude",
    "longitude",
    "velocity_kmh",
    "geometric_altitude_m",
    "on_ground",
    "last_contact",
]


def latest_artifact(pattern: str) -> Path | None:
    """Retorna o artefato mais recente pelo horário de modificação."""
    files = list((DATA_DIR / "data").glob(pattern))
    return max(files, key=lambda path: path.stat().st_mtime) if files else None


@st.cache_data(ttl=30)
def load_latest_records(limit: int = 200) -> pd.DataFrame:
    """Carrega aeronaves Gold atuais, limitando o volume entregue à UI."""
    latest_gold = latest_artifact("gold/latest/latest_aircraft_states-*.jsonl")
    if latest_gold:
        records = [
            json.loads(line)
            for line in latest_gold.read_text(encoding="utf-8").splitlines()
            if line
        ]
        return pd.DataFrame(records).head(limit)

    parquet_dir = DATA_DIR / "data" / "silver" / "aircraft_states"
    if not parquet_dir.exists():
        return pd.DataFrame(columns=EMPTY_COLUMNS)

    parquet_files = sorted(parquet_dir.glob("**/*.parquet"))
    if not parquet_files:
        return pd.DataFrame(columns=EMPTY_COLUMNS)

    query = "SELECT * FROM read_parquet(?) WHERE latitude IS NOT NULL AND longitude IS NOT NULL LIMIT ?"
    paths = [str(path) for path in parquet_files]
    con = duckdb.connect()
    try:
        df = con.execute(query, [paths, limit]).fetch_df()
    finally:
        con.close()
    return df


@st.cache_data(ttl=30)
def load_summary() -> dict:
    """Carrega o resumo Gold correspondente à última execução."""
    latest_summary = latest_artifact("gold/traffic/traffic_summary-*.jsonl")
    if not latest_summary:
        return {}
    lines = [
        line for line in latest_summary.read_text(encoding="utf-8").splitlines() if line
    ]
    return json.loads(lines[-1]) if lines else {}


@st.cache_data(ttl=30)
def load_run_reports() -> pd.DataFrame:
    """Carrega relatórios JSON para a aba de saúde do pipeline."""
    reports = []
    for path in sorted(
        (DATA_DIR / "data" / "observability").glob("*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    ):
        try:
            reports.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return pd.DataFrame(reports)


def report_table(reports: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nomes, status e durações para a apresentação operacional."""
    table = reports.copy()
    table["finished_at"] = pd.to_datetime(
        table["finished_at"], utc=True, errors="coerce"
    ).dt.tz_convert(SAO_PAULO_TZ)
    table["stage"] = (
        table["pipeline"]
        .map(
            {
                "collector": "Coleta",
                "bronze_to_silver": "Bronze → Silver",
                "silver_to_gold": "Silver → Gold",
            }
        )
        .fillna(table["pipeline"])
    )
    table["status_label"] = (
        table["status"]
        .map({"success": "OK", "failed": "Falhou"})
        .fillna(table["status"])
    )
    table["duration_label"] = table["duration_seconds"].map(
        lambda value: f"{value:.1f}s"
    )
    table["error_rate_label"] = (table["error_rate"].fillna(0) * 100).map(
        lambda value: f"{value:.1f}%"
    )
    return table.sort_values("finished_at", ascending=False)


def format_unix_timestamp(value: object) -> str:
    """Formata epoch Unix legado como horário UTC legível."""
    if pd.isna(value):
        return "N/D"
    timestamp = pd.to_datetime(value, unit="s", utc=True, errors="coerce")
    if pd.isna(timestamp):
        return "N/D"
    return timestamp.tz_convert(SAO_PAULO_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")


st.set_page_config(page_title="Brazil Air Traffic Beam", layout="wide")
st.title("Monitoramento aéreo")
st.caption(
    "Visão atual da região de São Paulo processada pelo pipeline OpenSky + Apache Beam"
)

if st.sidebar.button("Atualizar dados"):
    st.cache_data.clear()
    st.rerun()

df = load_latest_records(limit=500)
summary = load_summary()
reports = load_run_reports()

if df.empty:
    st.info(
        "Ainda não há dados Gold disponíveis. Execute a coleta, Bronze → Silver e Silver → Gold."
    )
    st.stop()

df["on_ground"] = df["on_ground"].fillna(False)
if "last_contact_at" in df:
    df["last_contact_display"] = (
        pd.to_datetime(df["last_contact_at"], utc=True, errors="coerce")
        .dt.tz_convert(SAO_PAULO_TZ)
        .dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    )
elif "last_contact" in df:
    df["last_contact_display"] = df["last_contact"].map(format_unix_timestamp)
countries = (
    sorted(df["origin_country"].dropna().unique()) if "origin_country" in df else []
)
selected_countries = st.sidebar.multiselect("País de origem", countries)
categories = (
    sorted(df["aircraft_category"].dropna().unique())
    if "aircraft_category" in df
    else []
)
selected_categories = st.sidebar.multiselect("Categoria da aeronave", categories)
status = st.sidebar.selectbox("Situação", ["Todas", "Em voo", "No solo"])
filtered = df.copy()
if selected_countries:
    filtered = filtered[filtered["origin_country"].isin(selected_countries)]
if selected_categories:
    filtered = filtered[filtered["aircraft_category"].isin(selected_categories)]
if status == "Em voo":
    filtered = filtered[~filtered["on_ground"]]
elif status == "No solo":
    filtered = filtered[filtered["on_ground"]]

airborne = int((~filtered["on_ground"]).sum())
average_speed = (
    filtered["velocity_kmh"].dropna().mean() if "velocity_kmh" in filtered else None
)
max_altitude = (
    filtered["geometric_altitude_m"].dropna().max()
    if "geometric_altitude_m" in filtered
    else None
)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Aeronaves", len(filtered), help="Aeronaves únicas na visão Gold")
col2.metric("Em voo", airborne)
col3.metric(
    "Velocidade média",
    f"{average_speed:.0f} km/h" if pd.notna(average_speed) else "N/D",
)
col4.metric(
    "Maior altitude", f"{max_altitude:,.0f} m" if pd.notna(max_altitude) else "N/D"
)

tab_map, tab_table, tab_quality = st.tabs(["Mapa", "Aeronaves", "Qualidade"])
with tab_map:
    map_data = filtered[["latitude", "longitude"]].dropna()
    st.map(map_data, size=14, zoom=7)
    st.caption(f"{len(map_data)} aeronaves com coordenadas válidas")

with tab_table:
    display_columns = [
        column
        for column in [
            "icao24",
            "callsign",
            "origin_country",
            "latitude",
            "longitude",
            "velocity_kmh",
            "barometric_altitude_m",
            "geometric_altitude_m",
            "true_track_degrees",
            "vertical_rate_mps",
            "aircraft_category",
            "squawk",
            "on_ground",
            "last_contact_display",
        ]
        if column in filtered
    ]
    labels = {
        "icao24": "Identificador",
        "callsign": "Callsign",
        "origin_country": "País",
        "latitude": "Latitude",
        "longitude": "Longitude",
        "velocity_kmh": "Velocidade (km/h)",
        "barometric_altitude_m": "Altitude barométrica (m)",
        "geometric_altitude_m": "Altitude (m)",
        "true_track_degrees": "Proa (graus)",
        "vertical_rate_mps": "Razão vertical (m/s)",
        "aircraft_category": "Categoria",
        "squawk": "Squawk",
        "on_ground": "No solo",
        "last_contact_display": "Último contato (SP)",
    }
    st.dataframe(
        filtered[display_columns].rename(columns=labels),
        use_container_width=True,
        hide_index=True,
    )

with tab_quality:
    if reports.empty:
        st.info("Ainda não existem relatórios de execução.")
    else:
        report_view = report_table(reports)
        latest_by_stage = report_view.drop_duplicates("pipeline")
        successful_stages = int((latest_by_stage["status"] == "success").sum())
        latest_rejected = int(
            latest_by_stage.loc[
                latest_by_stage["pipeline"] == "bronze_to_silver", "rejected_records"
            ].sum()
        )
        latest_duration = latest_by_stage["duration_seconds"].sum()
        last_update = report_view["finished_at"].iloc[0]
        metric1, metric2, metric3, metric4 = st.columns(4)
        metric1.metric("Etapas saudáveis", f"{successful_stages}/3")
        metric2.metric("Última atualização", last_update.strftime("%H:%M:%S %Z"))
        metric3.metric("Rejeitados", latest_rejected)
        metric4.metric("Tempo das etapas", f"{latest_duration:.1f}s")

        failed = latest_by_stage[latest_by_stage["status"] != "success"]
        if failed.empty:
            st.success("Todas as etapas da última execução concluíram com sucesso.")
        else:
            for _, failed_stage in failed.iterrows():
                st.error(
                    f"{failed_stage['stage']}: {failed_stage.get('error_message') or 'falha sem mensagem'}"
                )

        st.subheader("Saúde por etapa")
        stage_columns = [
            "stage",
            "status_label",
            "duration_label",
            "input_records",
            "output_records",
            "rejected_records",
            "error_rate_label",
        ]
        stage_labels = {
            "stage": "Etapa",
            "status_label": "Status",
            "duration_label": "Duração",
            "input_records": "Lidos",
            "output_records": "Gravados",
            "rejected_records": "Rejeitados",
            "error_rate_label": "Taxa de erro",
        }
        st.dataframe(
            latest_by_stage[stage_columns].rename(columns=stage_labels),
            use_container_width=True,
            hide_index=True,
        )

        if summary:
            st.subheader("Resultado Gold da última carga")
            gold_col1, gold_col2, gold_col3 = st.columns(3)
            gold_col1.metric("Observações", summary.get("aircraft_observations", 0))
            gold_col2.metric("Aeronaves únicas", summary.get("unique_aircraft", 0))
            gold_col3.metric("Em voo", summary.get("airborne_aircraft", 0))

        st.subheader("Histórico recente")
        history = report_view[
            ["stage", "status_label", "finished_at", "duration_label"]
        ].copy()
        history["finished_at"] = (
            history["finished_at"]
            .dt.tz_convert(SAO_PAULO_TZ)
            .dt.strftime("%Y-%m-%d %H:%M:%S %Z")
        )
        st.dataframe(
            history.head(12).rename(
                columns={
                    "stage": "Etapa",
                    "status_label": "Status",
                    "finished_at": "Finalizada em",
                    "duration_label": "Duração",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        with st.expander("Detalhes técnicos dos relatórios"):
            st.json(
                report_view.head(3)
                .drop(columns=["finished_at"], errors="ignore")
                .to_dict(orient="records")
            )
