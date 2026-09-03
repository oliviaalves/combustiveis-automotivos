import logging

import polars as pl

from combustiveis_automotivos.config import DELTA_TARGET, INFLACAO_DF, SILVER_TARGET

logger = logging.getLogger(__name__)


def transform_silver(dataframe: pl.DataFrame, inflacao_df: pl.DataFrame | None = None) -> pl.DataFrame:
    """
    Executa a transformação e limpeza dos dados brutos para a camada Silver:
    - Seleção de colunas relevantes
    - Renomeação padronizada
    - Conversão de tipos (vírgula decimal para Float64, datas para Date)
    - Extração de ano e mês de coleta
    - Saneamento de datas nulas e preços inválidos
    - Ajuste pela inflação histórica (quando fornecido)
    - Deduplicação por chaves primárias (incluindo CNPJ do posto)
    """
    colunas_obrigatorias = [
        "Estado - Sigla",
        "Municipio",
        "Produto",
        "Data da Coleta",
        "Valor de Venda",
        "Valor de Compra",
        "Unidade de Medida",
        "Bandeira",
    ]
    
    colunas_presentes = [c for c in colunas_obrigatorias if c in dataframe.columns]
    if len(colunas_presentes) < len(colunas_obrigatorias):
        faltantes = set(colunas_obrigatorias) - set(colunas_presentes)
        raise ValueError(f"Colunas obrigatórias ausentes no DataFrame: {faltantes}")

    select_exprs = [
        pl.col("Estado - Sigla").cast(pl.Utf8).alias("Estado_Sigla"),
        pl.col("Municipio").cast(pl.Utf8),
        pl.col("Produto").cast(pl.Utf8),
        pl.col("Bandeira").cast(pl.Utf8).str.strip_chars().alias("Bandeira"),
        pl.col("Unidade de Medida").cast(pl.Utf8).alias("Unidade_de_Medida"),
        pl.col("Data da Coleta").cast(pl.Utf8).str.to_date("%d/%m/%Y", strict=False).alias("Data_da_Coleta"),
        (
            pl.col("Valor de Venda")
            .cast(pl.Utf8)
            .str.replace(",", ".", literal=True)
            .cast(pl.Float64, strict=False)
            .alias("Valor_de_Venda")
        ),
        (
            pl.col("Valor de Compra")
            .cast(pl.Utf8)
            .str.replace(",", ".", literal=True)
            .cast(pl.Float64, strict=False)
            .alias("Valor_de_Compra")
        ),
    ]

    tem_cnpj = "CNPJ da Revenda" in dataframe.columns
    if tem_cnpj:
        # Normaliza CNPJ para apenas dígitos (remove espaços, pontos, barras, traços)
        select_exprs.append(
            pl.col("CNPJ da Revenda")
            .cast(pl.Utf8)
            .str.strip_chars()
            .str.replace_all(r"[^\d]", "", literal=False)
            .alias("CNPJ_da_Revenda")
        )

    transformed = dataframe.select(select_exprs).with_columns(
        Ano_de_coleta=pl.col("Data_da_Coleta").dt.year(),
        Mes_de_coleta=pl.col("Data_da_Coleta").dt.month(),
    )

    # Saneamento de qualidade: descarta datas inválidas/nulas e preços não positivos
    transformed = transformed.filter(
        pl.col("Data_da_Coleta").is_not_null()
        & pl.col("Ano_de_coleta").is_not_null()
        & (pl.col("Valor_de_Venda") > 0)
    )

    if inflacao_df is not None:
        if "fatores" in inflacao_df.columns:
            fatores_df = (
                inflacao_df.unnest("fatores")
                .unpivot(
                    index=[c for c in ["indice", "referencia"] if c in inflacao_df.columns],
                    variable_name="ano",
                    value_name="fator_inflacao",
                )
                .select(
                    pl.col("ano").cast(pl.Int32),
                    pl.col("fator_inflacao").cast(pl.Float64),
                )
            )
        else:
            fatores_df = inflacao_df.select(
                pl.col("ano").cast(pl.Int32),
                pl.col("fator_inflacao").cast(pl.Float64),
            )

        transformed = (
            transformed.join(fatores_df, left_on="Ano_de_coleta", right_on="ano", how="left")
            .with_columns(
                Valor_de_Venda_ajustado=(pl.col("Valor_de_Venda") * pl.col("fator_inflacao").fill_null(1.0)),
                Valor_de_Compra_ajustado=(pl.col("Valor_de_Compra") * pl.col("fator_inflacao").fill_null(1.0)),
            )
            .drop("fator_inflacao")
        )
    else:
        transformed = transformed.with_columns(
            Valor_de_Venda_ajustado=pl.col("Valor_de_Venda"),
            Valor_de_Compra_ajustado=pl.col("Valor_de_Compra"),
        )

    key_cols = ["Estado_Sigla", "Municipio", "Produto", "Data_da_Coleta", "Bandeira"]
    if tem_cnpj:
        key_cols.append("CNPJ_da_Revenda")

    return transformed.unique(subset=key_cols)


def generate_silver(anos: list[int] | None = None) -> None:
    """
    Gera a tabela silver de combustíveis automotivos a partir da tabela raw,
    com particionamento por Ano_de_coleta e suporte a filtro opcional por ano.
    Usa scan_delta para otimização de memória e proteção de partições Delta Lake.
    """
    from deltalake import DeltaTable

    try:
        lazy_df = pl.scan_delta(str(DELTA_TARGET))
        if anos is not None:
            lazy_df = lazy_df.filter(
                pl.col("Data da Coleta")
                .cast(pl.Utf8)
                .str.slice(-4)
                .cast(pl.Int32, strict=False)
                .is_in(anos)
            )
        dataframe = lazy_df.collect()
        inflacao_df = pl.read_json(str(INFLACAO_DF))

    except Exception:
        logger.exception("Erro ao ler o arquivo Delta da camada Raw")
        raise

    silver_df = transform_silver(dataframe, inflacao_df)

    SILVER_TARGET.parent.mkdir(parents=True, exist_ok=True)
    delta_opts = {"schema_mode": "overwrite", "partition_by": ["Ano_de_coleta"]}

    if anos is not None and DeltaTable.is_deltatable(str(SILVER_TARGET)):
        anos_str = ", ".join(str(a) for a in anos)
        delta_opts["predicate"] = f"Ano_de_coleta IN ({anos_str})"

    silver_df.write_delta(
        str(SILVER_TARGET),
        mode="overwrite",
        delta_write_options=delta_opts,
    )
    logger.info(f"Tabela Silver gerada com sucesso ({len(silver_df)} registros).")