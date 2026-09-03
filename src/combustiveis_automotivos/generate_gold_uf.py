import logging

from combustiveis_automotivos.config import SILVER_TARGET, UF_MES_GOLD_TARGET
from combustiveis_automotivos.gold_transformations import build_gold_layer

logger = logging.getLogger(__name__)

GRAIN_UF_MES = ["Estado_Sigla", "Produto", "Ano_de_coleta", "Mes_de_coleta"]


def ca_uf_mes_gold(anos: list[int] | None = None) -> None:
    """
    Gera a tabela Gold de combustíveis automotivos por UF e mês, a partir da tabela Silver,
    particionada por Ano_de_coleta e com suporte a filtro opcional por ano.
    """
    agg_df = build_gold_layer(
        source_target=SILVER_TARGET,
        output_target=UF_MES_GOLD_TARGET,
        grain_cols=GRAIN_UF_MES,
        anos=anos,
    )
    logger.info(f"Tabela Gold UF/Mês gerada com sucesso ({len(agg_df)} agregações).")
