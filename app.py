"""
Dashboard Interativo de Análise de Preços e Margens de Combustíveis Automotivos (ANP).
Utiliza dados da camada Gold (Delta Lake) agregados por UF/Mês e Município/Mês.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import polars as pl
import streamlit as st

from combustiveis_automotivos.config import (
    MUNICIPIO_MES_GOLD_TARGET,
    UF_MES_GOLD_TARGET,
)

# Configuração da Página
st.set_page_config(
    page_title="Combustíveis Brasil | Análise de Margens ANP",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilização CSS personalizada para visual premium
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .main-header {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid #334155;
            padding: 1.8rem 2.2rem;
            border-radius: 14px;
            margin-bottom: 1.8rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        }
        
        .main-header h1 {
            color: #f8fafc;
            font-size: 2.2rem;
            font-weight: 800;
            margin: 0;
            letter-spacing: -0.02em;
        }
        
        .main-header p {
            color: #94a3b8;
            font-size: 0.95rem;
            margin-top: 0.4rem;
            margin-bottom: 0;
        }

        .metric-card {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 1.2rem 1.4rem;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);
            transition: transform 0.15s ease, border-color 0.15s ease;
        }
        .metric-card:hover {
            border-color: #3b82f6;
            transform: translateY(-2px);
        }
        
        .metric-title {
            color: #94a3b8;
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .metric-value {
            color: #f8fafc;
            font-size: 1.85rem;
            font-weight: 800;
            margin-top: 0.3rem;
            letter-spacing: -0.02em;
        }
        
        .metric-sub {
            color: #64748b;
            font-size: 0.8rem;
            margin-top: 0.2rem;
        }

        .badge-tag {
            display: inline-block;
            padding: 0.2rem 0.6rem;
            font-size: 0.75rem;
            font-weight: 600;
            border-radius: 6px;
            background-color: rgba(59, 130, 246, 0.15);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 1.5rem;
            border-bottom: 1px solid #334155;
        }
        .stTabs [data-baseweb="tab"] {
            font-weight: 600;
            font-size: 0.95rem;
            padding-top: 0.75rem;
            padding-bottom: 0.75rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Carregando dados consolidados da camada Gold...")
def load_uf_gold_data() -> pd.DataFrame:
    """Carrega os dados Gold agregados por UF/Mês."""
    try:
        df = pl.read_delta(str(UF_MES_GOLD_TARGET))
        pdf = df.to_pandas()
        # Garantir tipos numéricos e ordenação
        pdf["Ano_de_coleta"] = pd.to_numeric(pdf["Ano_de_coleta"], errors="coerce")
        pdf["Mes_de_coleta"] = pd.to_numeric(pdf["Mes_de_coleta"], errors="coerce")
        pdf = pdf.dropna(subset=["Ano_de_coleta", "Mes_de_coleta"])
        pdf["Ano_de_coleta"] = pdf["Ano_de_coleta"].astype(int)
        pdf["Mes_de_coleta"] = pdf["Mes_de_coleta"].astype(int)
        pdf["Data_Ref"] = pd.to_datetime(
            pdf["Ano_de_coleta"].astype(str)
            + "-"
            + pdf["Mes_de_coleta"].astype(str)
            + "-01"
        )
        return pdf.sort_values(
            ["Ano_de_coleta", "Mes_de_coleta", "Estado_Sigla", "Produto"]
        )
    except Exception as e:  # noqa: BLE001
        st.error(f"Erro ao carregar tabela Gold UF/Mês: {e}")
        return pd.DataFrame()


@st.cache_data(show_spinner="Carregando dados municipais...")
def load_mcp_gold_data() -> pd.DataFrame:
    """Carrega os dados Gold agregados por Município/Mês."""
    try:
        df = pl.read_delta(str(MUNICIPIO_MES_GOLD_TARGET))
        pdf = df.to_pandas()
        pdf["Ano_de_coleta"] = pd.to_numeric(pdf["Ano_de_coleta"], errors="coerce")
        pdf["Mes_de_coleta"] = pd.to_numeric(pdf["Mes_de_coleta"], errors="coerce")
        pdf = pdf.dropna(subset=["Ano_de_coleta", "Mes_de_coleta"])
        pdf["Ano_de_coleta"] = pdf["Ano_de_coleta"].astype(int)
        pdf["Mes_de_coleta"] = pdf["Mes_de_coleta"].astype(int)
        return pdf
    except Exception as e:  # noqa: BLE001
        st.error(f"Erro ao carregar tabela Gold Município/Mês: {e}")
        return pd.DataFrame()


def format_currency(val: float | None) -> str:
    if val is None or np.isnan(val):
        return "-"
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent(val: float | None) -> str:
    if val is None or np.isnan(val):
        return "-"
    return f"{val:+.2f}%".replace(".", ",")


# --- Carga de Dados ---
df_uf = load_uf_gold_data()

if df_uf.empty:
    st.error(
        "Não foram encontrados dados na camada Gold. Por favor, execute o pipeline ETL."
    )
    st.stop()

# --- Sidebar / Filtros ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/gas-station.png", width=64)
    st.title("Filtros do Painel")
    st.markdown("Ajuste os parâmetros para filtrar todas as visualizações.")

    # Filtro de Anos
    min_ano = int(df_uf["Ano_de_coleta"].min())
    max_ano = int(df_uf["Ano_de_coleta"].max())

    anos_sel = st.slider(
        "📅 Período de Coleta (Anos)",
        min_value=min_ano,
        max_value=max_ano,
        value=(min_ano, max_ano),
        step=1,
    )

    # Filtro de Combustíveis
    todos_produtos = sorted(df_uf["Produto"].dropna().unique().tolist())
    produtos_default = [
        p
        for p in ["GASOLINA", "ETANOL", "DIESEL", "GNV", "GASOLINA ADITIVADA"]
        if p in todos_produtos
    ]
    if not produtos_default:
        produtos_default = todos_produtos[:3]

    produtos_sel = st.multiselect(
        "⛽ Tipo de Combustível / Produto",
        options=todos_produtos,
        default=produtos_default,
    )

    # Filtro de Estados
    todos_estados = sorted(df_uf["Estado_Sigla"].dropna().unique().tolist())
    selecionar_todos_estados = st.checkbox(
        "Selecionar todos os Estados (BR)", value=True
    )

    if selecionar_todos_estados:
        estados_sel = todos_estados
    else:
        estados_sel = st.multiselect(
            "📍 Estados (UF)",
            options=todos_estados,
            default=["SP", "RJ", "MG", "PR", "BA"],
        )

    st.markdown("---")
    st.markdown(
        """
        **Sobre os Dados:**
        - **Fonte:** ANP (Dados Abertos)
        - **Valores:** Ajustados pelo IPCA (Junho/2026)
        - **Margem:** `Valor Venda Médio - Valor Compra Médio`
        """
    )

# Aplicação dos Filtros no dataset UF
filtered_df = df_uf[
    (df_uf["Ano_de_coleta"] >= anos_sel[0])
    & (df_uf["Ano_de_coleta"] <= anos_sel[1])
    & (df_uf["Produto"].isin(produtos_sel))
    & (df_uf["Estado_Sigla"].isin(estados_sel))
]

# --- Cabeçalho Principal ---
st.markdown(
    """
    <div class="main-header">
        <h1>⛽ Painel Analítico: Margem de Lucro & Preços ANP</h1>
        <p>Análise temporal histórica, evolução da margem de revenda ano a ano e comparativos dinâmicos de combustíveis no Brasil.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if filtered_df.empty:
    st.warning(
        "Nenhum dado encontrado para a combinação de filtros selecionada. Ajuste os filtros na barra lateral."
    )
    st.stop()

# --- Abas Principais ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📈 Margem Ano a Ano (YoY)",
        "⚖️ Análise Comparativa",
        "📊 Visão Geral & KPIs",
        "🗺️ Ranking Regional & Municípios",
        "📋 Dados Detalhados",
    ]
)


# ==============================================================================
# ABA 1: MARGEM ANO A ANO (YOY) - FOCO PRINCIPAL SOLICITADO
# ==============================================================================
with tab1:
    st.markdown("### 📊 Evolução da Margem de Lucro Bruta Ano a Ano (YoY)")
    st.markdown(
        "Análise histórica do spread de revenda (Valor de Venda ajustado - Valor de Compra ajustado por litro)."
    )

    # Alerta informativo sobre a regulamentação da ANP
    st.info(
        "ℹ️ **Nota sobre os Dados da ANP:** Os dados de **2025 e 2026 (1º semestre)** estão carregados com sucesso "
        "para os **Preços de Venda**. Contudo, a ANP descontinuou a coleta obrigatória do campo *Valor de Compra* (custo da distribuidora) "
        "a partir de 2022. Por isso, as margens de revenda são calculadas para o período de 2004 a 2021."
    )

    # Agregação Anual
    df_anual = (
        filtered_df.dropna(subset=["Margem_media"])
        .groupby(["Ano_de_coleta", "Produto"], as_index=False)
        .agg(
            Margem_media=("Margem_media", "mean"),
            Margem_mediana=("Margem_media", "median"),
            Valor_de_Venda_medio=("Valor_de_Venda_medio", "mean"),
            Valor_de_Compra_medio=("Valor_de_Compra_medio", "mean"),
        )
        .sort_values(["Produto", "Ano_de_coleta"])
    )

    # Cálculo da Taxa de Crescimento YoY da Margem
    df_anual["Margem_YoY_%"] = (
        df_anual.groupby("Produto")["Margem_media"].pct_change() * 100
    )
    df_anual["Venda_YoY_%"] = (
        df_anual.groupby("Produto")["Valor_de_Venda_medio"].pct_change() * 100
    )
    df_anual["Margem_Percentual"] = (
        df_anual["Margem_media"] / df_anual["Valor_de_Venda_medio"]
    ) * 100

    col_chart1, col_chart2 = st.columns([3, 2])

    with col_chart1:
        # Gráfico de Linhas: Margem de Lucro Ano a Ano
        fig_margin_yoy = px.line(
            df_anual,
            x="Ano_de_coleta",
            y="Margem_media",
            color="Produto",
            markers=True,
            title="<b>Margem de Revenda Média por Ano (R$/litro ajustado pelo IPCA)</b>",
            labels={
                "Ano_de_coleta": "Ano",
                "Margem_media": "Margem Média (R$/L)",
                "Produto": "Combustível",
            },
            template="plotly_dark",
        )
        fig_margin_yoy.update_traces(line={"width": 3}, marker={"size": 7})
        fig_margin_yoy.update_layout(
            hovermode="x unified",
            margin={"l": 20, "r": 20, "t": 50, "b": 20},
            legend={
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1,
            },
        )
        st.plotly_chart(fig_margin_yoy, use_container_width=True)

    with col_chart2:
        # Gráfico de Barras: Margem Percentual sobre o Preço de Venda
        fig_margin_pct = px.bar(
            df_anual,
            x="Ano_de_coleta",
            y="Margem_Percentual",
            color="Produto",
            barmode="group",
            title="<b>Margem Bruta Percentual (% do Preço de Venda)</b>",
            labels={
                "Ano_de_coleta": "Ano",
                "Margem_Percentual": "Margem (%)",
                "Produto": "Combustível",
            },
            template="plotly_dark",
        )
        fig_margin_pct.update_layout(
            hovermode="x unified",
            margin={"l": 20, "r": 20, "t": 50, "b": 20},
            legend={
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1,
            },
        )
        st.plotly_chart(fig_margin_pct, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 🔄 Variação Percentual Ano a Ano (YoY Growth Rate da Margem)")

    # Gráfico de Variação YoY (%)
    fig_yoy_growth = px.bar(
        df_anual.dropna(subset=["Margem_YoY_%"]),
        x="Ano_de_coleta",
        y="Margem_YoY_%",
        color="Produto",
        barmode="group",
        title="<b>Variação Anual da Margem de Lucro (% YoY)</b>",
        labels={
            "Ano_de_coleta": "Ano",
            "Margem_YoY_%": "Crescimento da Margem (%)",
            "Produto": "Combustível",
        },
        template="plotly_dark",
    )
    fig_yoy_growth.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.4)")
    fig_yoy_growth.update_layout(
        hovermode="x unified",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
    )
    st.plotly_chart(fig_yoy_growth, use_container_width=True)

    # Tabela Resumo YoY
    st.markdown("#### 📋 Tabela Analítica de Evolução Anual")
    tabela_yoy = df_anual.copy()
    tabela_yoy_display = tabela_yoy.rename(
        columns={
            "Ano_de_coleta": "Ano",
            "Produto": "Produto",
            "Valor_de_Venda_medio": "Venda Média (R$/L)",
            "Valor_de_Compra_medio": "Compra Média (R$/L)",
            "Margem_media": "Margem Média (R$/L)",
            "Margem_Percentual": "Margem (%)",
            "Margem_YoY_%": "Variação Margem YoY (%)",
        }
    )

    st.dataframe(
        tabela_yoy_display[
            [
                "Ano",
                "Produto",
                "Venda Média (R$/L)",
                "Compra Média (R$/L)",
                "Margem Média (R$/L)",
                "Margem (%)",
                "Variação Margem YoY (%)",
            ]
        ].style.format(
            {
                "Venda Média (R$/L)": "R$ {:.2f}",
                "Compra Média (R$/L)": "R$ {:.2f}",
                "Margem Média (R$/L)": "R$ {:.2f}",
                "Margem (%)": "{:.2f}%",
                "Variação Margem YoY (%)": "{:+.2f}%",
            },
            na_rep="-",
        ),
        use_container_width=True,
    )


# ==============================================================================
# ABA 2: ANÁLISE COMPARATIVA MULTIDIMENSIONAL
# ==============================================================================
with tab2:
    st.markdown("### ⚖️ Comparativos Dinâmicos")

    comp_subtab1, comp_subtab2, comp_subtab3 = st.tabs(
        [
            "⛽ Comparativo entre Combustíveis & Paridade",
            "📍 Comparativo entre Estados (UFs)",
            "📅 Comparativo Entre Dois Anos Específicos",
        ]
    )

    with comp_subtab1:
        st.markdown("#### Comparação Direta de Margem & Preço entre Combustíveis")

        # Gráfico de dispersão / bolhas: Preço de Compra vs Preço de Venda com tamanho = Margem
        df_comp_prod = (
            filtered_df.dropna(subset=["Margem_media"])
            .groupby(["Ano_de_coleta", "Produto"], as_index=False)
            .agg(
                Valor_de_Venda_medio=("Valor_de_Venda_medio", "mean"),
                Valor_de_Compra_medio=("Valor_de_Compra_medio", "mean"),
                Margem_media=("Margem_media", "mean"),
            )
        )

        fig_scatter = px.scatter(
            df_comp_prod,
            x="Valor_de_Compra_medio",
            y="Valor_de_Venda_medio",
            size="Margem_media",
            color="Produto",
            hover_data=["Ano_de_coleta", "Margem_media"],
            title="<b>Correlação Preço de Compra x Preço de Venda (Tamanho do Ponto = Margem de Lucro)</b>",
            labels={
                "Valor_de_Compra_medio": "Preço de Compra Médio (R$/L)",
                "Valor_de_Venda_medio": "Preço de Venda Médio (R$/L)",
                "Margem_media": "Margem Média (R$/L)",
            },
            template="plotly_dark",
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

        # Análise Especial: Paridade Etanol vs Gasolina (Regra dos 70%)
        if (
            "GASOLINA" in filtered_df["Produto"].values
            and "ETANOL" in filtered_df["Produto"].values
        ):
            st.markdown("#### ⚡ Paridade de Preços: Etanol vs Gasolina (Relação 70%)")
            st.info(
                "Pela regra clássica de eficiência energética veicular, o etanol é economicamente vantajoso quando seu preço representa até 70% do preço da gasolina."
            )

            df_gas = (
                filtered_df[filtered_df["Produto"] == "GASOLINA"]
                .groupby(["Ano_de_coleta", "Mes_de_coleta"], as_index=False)[
                    "Valor_de_Venda_medio"
                ]
                .mean()
            )
            df_eta = (
                filtered_df[filtered_df["Produto"] == "ETANOL"]
                .groupby(["Ano_de_coleta", "Mes_de_coleta"], as_index=False)[
                    "Valor_de_Venda_medio"
                ]
                .mean()
            )

            df_paridade = pd.merge(
                df_gas,
                df_eta,
                on=["Ano_de_coleta", "Mes_de_coleta"],
                suffixes=("_Gasolina", "_Etanol"),
            )
            df_paridade["Razao_Etanol_Gasolina"] = (
                df_paridade["Valor_de_Venda_medio_Etanol"]
                / df_paridade["Valor_de_Venda_medio_Gasolina"]
            ) * 100
            df_paridade["Data_Ref"] = pd.to_datetime(
                df_paridade["Ano_de_coleta"].astype(str)
                + "-"
                + df_paridade["Mes_de_coleta"].astype(str)
                + "-01"
            )
            df_paridade = df_paridade.sort_values("Data_Ref")

            fig_paridade = go.Figure()
            fig_paridade.add_trace(
                go.Scatter(
                    x=df_paridade["Data_Ref"],
                    y=df_paridade["Razao_Etanol_Gasolina"],
                    mode="lines",
                    name="Razão Etanol / Gasolina (%)",
                    line={"color": "#10b981", "width": 2.5},
                )
            )
            fig_paridade.add_hline(
                y=70.0,
                line_dash="dash",
                line_color="#ef4444",
                annotation_text="Limite de Paridade (70%)",
                annotation_position="top right",
            )
            fig_paridade.update_layout(
                title="<b>Histórico da Paridade de Preço de Venda (Etanol / Gasolina %)</b>",
                xaxis_title="Período",
                yaxis_title="Relação Preço (%)",
                template="plotly_dark",
                margin={"l": 20, "r": 20, "t": 50, "b": 20},
            )
            st.plotly_chart(fig_paridade, use_container_width=True)

    with comp_subtab2:
        st.markdown("#### Comparativo de Margens entre Estados (UFs)")

        estados_comp_sel = st.multiselect(
            "Selecione Estados para Comparar:",
            options=todos_estados,
            default=["SP", "RJ", "MG", "PR", "BA"]
            if {"SP", "RJ", "MG", "PR", "BA"}.issubset(todos_estados)
            else todos_estados[:4],
            key="comp_ufs",
        )
        prod_comp_uf = st.selectbox(
            "Combustível para o Comparativo de Estados:",
            options=produtos_sel,
            index=0,
            key="comp_uf_prod",
        )

        if estados_comp_sel:
            df_comp_uf = (
                df_uf[
                    (df_uf["Estado_Sigla"].isin(estados_comp_sel))
                    & (df_uf["Produto"] == prod_comp_uf)
                    & (df_uf["Ano_de_coleta"] >= anos_sel[0])
                    & (df_uf["Ano_de_coleta"] <= anos_sel[1])
                ]
                .groupby(["Ano_de_coleta", "Estado_Sigla"], as_index=False)[
                    "Margem_media"
                ]
                .mean()
            )

            fig_comp_uf = px.line(
                df_comp_uf,
                x="Ano_de_coleta",
                y="Margem_media",
                color="Estado_Sigla",
                markers=True,
                title=f"<b>Margem Média de {prod_comp_uf} por Estado ao Longo dos Anos (R$/L)</b>",
                labels={
                    "Ano_de_coleta": "Ano",
                    "Margem_media": "Margem Média (R$/L)",
                    "Estado_Sigla": "UF",
                },
                template="plotly_dark",
            )
            fig_comp_uf.update_traces(line={"width": 2.5})
            fig_comp_uf.update_layout(
                hovermode="x unified", margin={"l": 20, "r": 20, "t": 50, "b": 20}
            )
            st.plotly_chart(fig_comp_uf, use_container_width=True)

    with comp_subtab3:
        st.markdown("#### Comparativo Detalhado entre Dois Anos Selecionados")

        col_ano_a, col_ano_b = st.columns(2)
        with col_ano_a:
            ano_base = st.selectbox(
                "Ano Base (A):",
                options=sorted(df_uf["Ano_de_coleta"].unique(), reverse=True),
                index=min(5, len(df_uf["Ano_de_coleta"].unique()) - 1),
            )
        with col_ano_b:
            ano_comp = st.selectbox(
                "Ano de Comparação (B):",
                options=sorted(df_uf["Ano_de_coleta"].unique(), reverse=True),
                index=0,
            )

        df_ano_a = (
            df_uf[df_uf["Ano_de_coleta"] == ano_base]
            .groupby("Produto", as_index=False)
            .agg(
                Venda_A=("Valor_de_Venda_medio", "mean"),
                Compra_A=("Valor_de_Compra_medio", "mean"),
                Margem_A=("Margem_media", "mean"),
            )
        )
        df_ano_b = (
            df_uf[df_uf["Ano_de_coleta"] == ano_comp]
            .groupby("Produto", as_index=False)
            .agg(
                Venda_B=("Valor_de_Venda_medio", "mean"),
                Compra_B=("Valor_de_Compra_medio", "mean"),
                Margem_B=("Margem_media", "mean"),
            )
        )

        df_diff = pd.merge(df_ano_a, df_ano_b, on="Produto", how="inner")
        df_diff["Delta_Margem_R$"] = df_diff["Margem_B"] - df_diff["Margem_A"]
        df_diff["Delta_Margem_%"] = (
            (df_diff["Margem_B"] - df_diff["Margem_A"]) / df_diff["Margem_A"]
        ) * 100
        df_diff["Delta_Venda_R$"] = df_diff["Venda_B"] - df_diff["Venda_A"]

        # Gráfico comparativo de barras lado a lado
        fig_diff_bar = go.Figure()
        fig_diff_bar.add_trace(
            go.Bar(
                name=f"Ano {ano_base}",
                x=df_diff["Produto"],
                y=df_diff["Margem_A"],
                marker_color="#64748b",
            )
        )
        fig_diff_bar.add_trace(
            go.Bar(
                name=f"Ano {ano_comp}",
                x=df_diff["Produto"],
                y=df_diff["Margem_B"],
                marker_color="#3b82f6",
            )
        )
        fig_diff_bar.update_layout(
            barmode="group",
            title=f"<b>Comparativo de Margem de Lucro: {ano_base} vs {ano_comp} (R$/L)</b>",
            xaxis_title="Produto",
            yaxis_title="Margem Média (R$/L)",
            template="plotly_dark",
            margin={"l": 20, "r": 20, "t": 50, "b": 20},
        )
        st.plotly_chart(fig_diff_bar, use_container_width=True)

        st.dataframe(
            df_diff.rename(
                columns={
                    "Produto": "Produto",
                    "Margem_A": f"Margem {ano_base} (R$/L)",
                    "Margem_B": f"Margem {ano_comp} (R$/L)",
                    "Delta_Margem_R$": "Variação Absoluta (R$/L)",
                    "Delta_Margem_%": "Variação Percentual (%)",
                    "Venda_A": f"Venda {ano_base} (R$/L)",
                    "Venda_B": f"Venda {ano_comp} (R$/L)",
                }
            ).style.format(
                {
                    f"Margem {ano_base} (R$/L)": "R$ {:.2f}",
                    f"Margem {ano_comp} (R$/L)": "R$ {:.2f}",
                    "Variação Absoluta (R$/L)": "R$ {:+.2f}",
                    "Variação Percentual (%)": "{:+.2f}%",
                    f"Venda {ano_base} (R$/L)": "R$ {:.2f}",
                    f"Venda {ano_comp} (R$/L)": "R$ {:.2f}",
                },
                na_rep="-",
            ),
            use_container_width=True,
        )


# ==============================================================================
# ABA 3: VISÃO GERAL & KPIS CONSOLIDADOS
# ==============================================================================
with tab3:
    st.markdown("### 📊 Visão Geral Consolidada")

    venda_media_geral = filtered_df["Valor_de_Venda_medio"].mean()
    compra_media_geral = (
        filtered_df["Valor_de_Compra_medio"].dropna().mean()
        if not filtered_df["Valor_de_Compra_medio"].dropna().empty
        else None
    )
    margem_media_geral = (
        filtered_df["Margem_media"].dropna().mean()
        if not filtered_df["Margem_media"].dropna().empty
        else None
    )
    margem_pct_geral = (
        (margem_media_geral / venda_media_geral * 100)
        if (margem_media_geral and venda_media_geral)
        else None
    )

    # Cards de KPIs
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Margem de Lucro Média</div>
                <div class="metric-value">{format_currency(margem_media_geral)} / L</div>
                <div class="metric-sub">Spread médio de revenda</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with kpi2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Margem Bruta %</div>
                <div class="metric-value">{f"{margem_pct_geral:.1f}%" if margem_pct_geral else "-"}</div>
                <div class="metric-sub">% sobre preço na bomba</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with kpi3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Preço de Venda Médio</div>
                <div class="metric-value">{format_currency(venda_media_geral)} / L</div>
                <div class="metric-sub">Ajustado pelo IPCA</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with kpi4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Preço de Compra Médio</div>
                <div class="metric-value">{format_currency(compra_media_geral)} / L</div>
                <div class="metric-sub">Custo de aquisição do posto</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Gráfico de Decomposição: Venda vs Compra vs Margem ao Longo do Tempo
    df_tempo = (
        filtered_df.groupby("Data_Ref", as_index=False)
        .agg(
            Valor_de_Venda_medio=("Valor_de_Venda_medio", "mean"),
            Valor_de_Compra_medio=("Valor_de_Compra_medio", "mean"),
            Margem_media=("Margem_media", "mean"),
        )
        .sort_values("Data_Ref")
    )

    fig_decomp = go.Figure()
    fig_decomp.add_trace(
        go.Scatter(
            x=df_tempo["Data_Ref"],
            y=df_tempo["Valor_de_Venda_medio"],
            mode="lines",
            name="Preço de Venda (Bomba)",
            line={"color": "#38bdf8", "width": 2},
        )
    )
    fig_decomp.add_trace(
        go.Scatter(
            x=df_tempo["Data_Ref"],
            y=df_tempo["Valor_de_Compra_medio"],
            mode="lines",
            name="Preço de Compra (Distribuidora)",
            line={"color": "#fbbf24", "width": 2},
        )
    )
    fig_decomp.add_trace(
        go.Bar(
            x=df_tempo["Data_Ref"],
            y=df_tempo["Margem_media"],
            name="Margem Bruta (Spread)",
            marker_color="rgba(16, 185, 129, 0.4)",
        )
    )
    fig_decomp.update_layout(
        title="<b>Composição Histórica Mensal: Preço de Venda, Custo de Compra e Margem</b>",
        xaxis_title="Data",
        yaxis_title="Preço (R$/Litro ajustado)",
        hovermode="x unified",
        template="plotly_dark",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
    )
    st.plotly_chart(fig_decomp, use_container_width=True)


# ==============================================================================
# ABA 4: RANKING REGIONAL & MUNICÍPIOS
# ==============================================================================
with tab4:
    st.markdown("### 🗺️ Rankings Geográficos e Detalhamento Municipal")

    col_rank_uf, col_rank_mcp = st.columns([1, 1])

    with col_rank_uf:
        st.markdown("#### 🏆 Ranking de Margens por Estado (UF)")
        df_rank_uf = (
            filtered_df.dropna(subset=["Margem_media"])
            .groupby("Estado_Sigla", as_index=False)["Margem_media"]
            .mean()
            .sort_values("Margem_media", ascending=True)
        )

        fig_rank_uf = px.bar(
            df_rank_uf,
            x="Margem_media",
            y="Estado_Sigla",
            orientation="h",
            title="<b>Margem Média de Revenda por UF (R$/L)</b>",
            labels={"Margem_media": "Margem Média (R$/L)", "Estado_Sigla": "UF"},
            color="Margem_media",
            color_continuous_scale="Viridis",
            template="plotly_dark",
        )
        fig_rank_uf.update_layout(
            margin={"l": 20, "r": 20, "t": 50, "b": 20}, height=550
        )
        st.plotly_chart(fig_rank_uf, use_container_width=True)

    with col_rank_mcp:
        st.markdown("#### 🏙️ Detalhamento por Município")
        st.markdown("Explore municípios com maiores e menores margens de lucro.")

        df_mcp = load_mcp_gold_data()
        if not df_mcp.empty:
            df_mcp_filt = df_mcp[
                (df_mcp["Ano_de_coleta"] >= anos_sel[0])
                & (df_mcp["Ano_de_coleta"] <= anos_sel[1])
                & (df_mcp["Produto"].isin(produtos_sel))
                & (df_mcp["Estado_Sigla"].isin(estados_sel))
            ].dropna(subset=["Margem_media"])

            if not df_mcp_filt.empty:
                df_mcp_top = (
                    df_mcp_filt.groupby(["Estado_Sigla", "Municipio"], as_index=False)
                    .agg(
                        Margem_media=("Margem_media", "mean"),
                        Valor_de_Venda_medio=("Valor_de_Venda_medio", "mean"),
                        Valor_de_Compra_medio=("Valor_de_Compra_medio", "mean"),
                    )
                    .sort_values("Margem_media", ascending=False)
                )

                st.markdown("**Top 10 Municípios com Maior Margem Média:**")
                st.dataframe(
                    df_mcp_top.head(10).style.format(
                        {
                            "Margem_media": "R$ {:.2f}",
                            "Valor_de_Venda_medio": "R$ {:.2f}",
                            "Valor_de_Compra_medio": "R$ {:.2f}",
                        }
                    ),
                    use_container_width=True,
                )

                st.markdown("**Top 10 Municípios com Menor Margem Média:**")
                st.dataframe(
                    df_mcp_top.tail(10)
                    .sort_values("Margem_media")
                    .style.format(
                        {
                            "Margem_media": "R$ {:.2f}",
                            "Valor_de_Venda_medio": "R$ {:.2f}",
                            "Valor_de_Compra_medio": "R$ {:.2f}",
                        }
                    ),
                    use_container_width=True,
                )


# ==============================================================================
# ABA 5: TABELA DE DADOS & EXPORTAÇÃO
# ==============================================================================
with tab5:
    st.markdown("### 📋 Base de Dados Filtrada")
    st.markdown(
        "Visualize os registros agregados da camada Gold e realize o download em CSV."
    )

    st.dataframe(
        filtered_df[
            [
                "Ano_de_coleta",
                "Mes_de_coleta",
                "Estado_Sigla",
                "Produto",
                "Valor_de_Venda_medio",
                "Valor_de_Compra_medio",
                "Margem_media",
                "Valor_de_Venda_min",
                "Valor_de_Venda_max",
            ]
        ]
        .rename(
            columns={
                "Ano_de_coleta": "Ano",
                "Mes_de_coleta": "Mês",
                "Estado_Sigla": "UF",
                "Produto": "Produto",
                "Valor_de_Venda_medio": "Venda Média (R$)",
                "Valor_de_Compra_medio": "Compra Média (R$)",
                "Margem_media": "Margem Média (R$)",
                "Valor_de_Venda_min": "Venda Mínima (R$)",
                "Valor_de_Venda_max": "Venda Máxima (R$)",
            }
        )
        .style.format(
            {
                "Venda Média (R$)": "R$ {:.2f}",
                "Compra Média (R$)": "R$ {:.2f}",
                "Margem Média (R$)": "R$ {:.2f}",
                "Venda Mínima (R$)": "R$ {:.2f}",
                "Venda Máxima (R$)": "R$ {:.2f}",
            },
            na_rep="-",
        ),
        use_container_width=True,
    )

    csv_data = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Baixar Dados Filtrados em CSV",
        data=csv_data,
        file_name="combustiveis_gold_filtrado.csv",
        mime="text/csv",
    )
