import logging

import polars as pl

from combustiveis_automotivos.config import SILVER_TARGET, UF_MES_GOLD_TARGET
from combustiveis_automotivos.gold_transformations import aggregate_gold

logger = logging.getLogger(__name__)

GRAIN_UF_MES = ["Estado_Sigla", "Produto", "Ano_de_coleta", "Mes_de_coleta"]


def ca_uf_mes_gold(anos: list[int] | None = None) -> None:
    """
    Gera a tabela Gold de combustíveis automotivos por UF e mês, a partir da tabela Silver,
    particionada por Ano_de_coleta e com suporte a filtro opcional por ano.
    """
    try:
        dataframe = pl.read_delta(str(SILVER_TARGET))
    except Exception:
        logger.exception("Erro ao ler o arquivo Delta da camada Silver")
        raise 

    if anos is not None:
        dataframe = dataframe.filter(pl.col("Ano_de_coleta").is_in(anos))

    valor_por_uf_por_mes = aggregate_gold(dataframe, grain_cols=GRAIN_UF_MES)

    UF_MES_GOLD_TARGET.parent.mkdir(parents=True, exist_ok=True)
    valor_por_uf_por_mes.write_delta(
        str(UF_MES_GOLD_TARGET),
        mode="overwrite",
        delta_write_options={"schema_mode": "overwrite", "partition_by": ["Ano_de_coleta"]},
    )
    logger.info(f"Tabela Gold UF/Mês gerada com sucesso ({len(valor_por_uf_por_mes)} agregações).")
