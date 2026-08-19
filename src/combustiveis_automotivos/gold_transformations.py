"""
Módulo de transformações e agregações da camada Gold.
"""

import polars as pl


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