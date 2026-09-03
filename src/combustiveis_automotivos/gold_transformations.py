"""
Módulo de transformações e agregações da camada Gold.
"""

import logging
from pathlib import Path

import polars as pl
from deltalake import DeltaTable

logger = logging.getLogger(__name__)


def aggregate_gold(dataframe: pl.DataFrame, grain_cols: list[str]) -> pl.DataFrame:
    """
    Realiza agregações analíticas (médias, máximos e mínimos de preços de venda e compra)
    a partir de um grão dimensional especificado (ex: por UF/mês ou por Município/mês).
    """
    for col in grain_cols:
        if col not in dataframe.columns:
            raise ValueError(f"Coluna dimensional obrigatória '{col}' ausente no DataFrame.")

    for metric in ["Valor_de_Venda_ajustado", "Valor_de_Compra_ajustado"]:
        if metric not in dataframe.columns:
            raise ValueError(f"Métrica obrigatória '{metric}' ausente no DataFrame.")

    agg_df = dataframe.group_by(grain_cols).agg([
        pl.col("Valor_de_Venda_ajustado").mean().alias("Valor_de_Venda_medio"),
        pl.col("Valor_de_Compra_ajustado").mean().alias("Valor_de_Compra_medio"),
        pl.col("Valor_de_Venda_ajustado").median().alias("Valor_de_Venda_mediana"),
        pl.col("Valor_de_Compra_ajustado").median().alias("Valor_de_Compra_mediana"),
        pl.col("Valor_de_Venda_ajustado").max().alias("Valor_de_Venda_max"),
        pl.col("Valor_de_Compra_ajustado").max().alias("Valor_de_Compra_max"),
        pl.col("Valor_de_Venda_ajustado").min().alias("Valor_de_Venda_min"),
        pl.col("Valor_de_Compra_ajustado").min().alias("Valor_de_Compra_min"),
    ])

    return agg_df.with_columns(
        Margem_media=pl.col("Valor_de_Venda_medio") - pl.col("Valor_de_Compra_medio"),
    )


def build_gold_layer(
    source_target: "Path",
    output_target: "Path",
    grain_cols: list[str],
    anos: list[int] | None = None,
    partition_cols: list[str] | None = None,
) -> pl.DataFrame:
    """
    Função unificada para carregar dados da camada Silver, filtrar por anos com pushdown lazy,
    agregar segundo o grão dimensional e gravar na camada Gold Delta Lake com particionamento seguro.
    """
    if partition_cols is None:
        partition_cols = ["Ano_de_coleta"]

    try:
        lazy_df = pl.scan_delta(str(source_target))
        if anos is not None:
            lazy_df = lazy_df.filter(pl.col("Ano_de_coleta").is_in(anos))
        dataframe = lazy_df.collect()
    except Exception:
        logger.exception(f"Erro ao ler os dados Delta de {source_target}")
        raise

    aggregated_df = aggregate_gold(dataframe, grain_cols=grain_cols)

    output_target.parent.mkdir(parents=True, exist_ok=True)
    delta_opts = {
        "schema_mode": "overwrite",
        "partition_by": partition_cols,
    }

    if anos is not None and DeltaTable.is_deltatable(str(output_target)):
        anos_str = ", ".join(str(a) for a in anos)
        delta_opts["predicate"] = f"Ano_de_coleta IN ({anos_str})"

    aggregated_df.write_delta(
        str(output_target),
        mode="overwrite",
        delta_write_options=delta_opts,
    )
    return aggregated_df