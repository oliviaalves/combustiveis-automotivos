import logging

from combustiveis_automotivos.config import (
    MUNICIPIO_MES_GOLD_TARGET,
    SILVER_TARGET,
)
from combustiveis_automotivos.gold_transformations import build_gold_layer

logger = logging.getLogger(__name__)

GRAIN_MUNICIPIO_MES = ["Estado_Sigla", "Municipio", "Produto", "Ano_de_coleta", "Mes_de_coleta"]


def ca_municipio_mes_gold(anos: list[int] | None = None) -> None:
    """
    Gera a tabela Gold de combustíveis automotivos por município e mês, a partir da tabela Silver,
    particionada por Ano_de_coleta e com suporte a filtro opcional por ano.
    Inclui Estado_Sigla no agrupamento para evitar colisão entre municípios homônimos de estados diferentes.
    """
    agg_df = build_gold_layer(
        source_target=SILVER_TARGET,
        output_target=MUNICIPIO_MES_GOLD_TARGET,
        grain_cols=GRAIN_MUNICIPIO_MES,
        anos=anos,
    )
    logger.info(
        f"Tabela Gold Município/Mês gerada com sucesso ({len(agg_df)} agregações)."
    )