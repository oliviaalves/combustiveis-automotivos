import logging

import polars as pl

from combustiveis_automotivos.config import (
    MUNICIPIO_MES_GOLD_TARGET,
    SILVER_TARGET,
)
from combustiveis_automotivos.gold_transformations import aggregate_gold

logger = logging.getLogger(__name__)

GRAIN_MUNICIPIO_MES = ["Estado_Sigla", "Municipio", "Produto", "Ano_de_coleta", "Mes_de_coleta"]


def ca_municipio_mes_gold(anos: list[int] | None = None) -> None:
    """
    Gera a tabela Gold de combustíveis automotivos por município e mês, a partir da tabela Silver,
    particionada por Ano_de_coleta e com suporte a filtro opcional por ano.
    Inclui Estado_Sigla no agrupamento para evitar colisão entre municípios homônimos de estados diferentes.
    """
    try:
        dataframe = pl.read_delta(str(SILVER_TARGET))
    except Exception as e:
        logger.exception("Erro ao ler o arquivo Delta da camada Silver")
        raise e

    if anos is not None:
        dataframe = dataframe.filter(pl.col("Ano_de_coleta").is_in(anos))

    valor_por_municipio_por_mes = aggregate_gold(dataframe, grain_cols=GRAIN_MUNICIPIO_MES)

    MUNICIPIO_MES_GOLD_TARGET.parent.mkdir(parents=True, exist_ok=True)
    valor_por_municipio_por_mes.write_delta(
        str(MUNICIPIO_MES_GOLD_TARGET),
        mode="overwrite",
        delta_write_options={"schema_mode": "overwrite", "partition_by": ["Ano_de_coleta"]},
    )
    logger.info(
        f"Tabela Gold Município/Mês gerada com sucesso ({len(valor_por_municipio_por_mes)} agregações)."
    )