import argparse
import logging
import sys
from datetime import UTC, datetime

from combustiveis_automotivos.collect_data import collect_data
from combustiveis_automotivos.generate_gold_mcp import (
    ca_municipio_mes_gold,
)
from combustiveis_automotivos.generate_gold_uf import (
    ca_uf_mes_gold,
)
from combustiveis_automotivos.generate_silver import generate_silver
from combustiveis_automotivos.parse_data import parse_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger: logging.Logger = logging.getLogger(__name__)

ALL_STEPS = ["collect", "parse", "silver", "gold"]


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pipeline ETL de Preços de Combustíveis Automotivos (ANP) com Polars e Delta Lake."
    )
    parser.add_argument(
        "--steps",
        nargs="+",
        choices=ALL_STEPS,
        default=ALL_STEPS,
        help="Etapas do pipeline a serem executadas. Padrão: todas (collect, parse, silver, gold).",
    )
    parser.add_argument(
        "--ano-inicio",
        type=int,
        default=None,
        help="Ano inicial para a coleta de dados (opcional, aplicável à etapa 'collect').",
    )
    parser.add_argument(
        "--ano-fim",
        type=int,
        default=None,
        help="Ano final para a coleta de dados (opcional, aplicável à etapa 'collect').",
    )
    return parser.parse_args(args)


def run_pipeline(
    steps: list[str] | None = None,
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
) -> None:
    selected_steps = steps or ALL_STEPS
    start_time = datetime.now(tz=UTC)
    logger.info(f"Iniciando pipeline de combustíveis automotivos. Etapas selecionadas: {selected_steps}")

    anos = None
    if ano_inicio is not None or ano_fim is not None:
        ini = ano_inicio if ano_inicio is not None else 2004
        fim = ano_fim if ano_fim is not None else 2026
        anos = list(range(ini, fim + 1))

    if "collect" in selected_steps:
        logger.info("-> Executando etapa: Coleta de Dados (collect)...")
        collect_data(ano_inicio=ano_inicio, ano_fim=ano_fim)

    if "parse" in selected_steps:
        logger.info("-> Executando etapa: Ingestão Raw Delta (parse)...")
        parse_data()

    if "silver" in selected_steps:
        logger.info("-> Executando etapa: Transformação Silver Delta (silver)...")
        generate_silver(anos=anos)

    if "gold" in selected_steps:
        logger.info("-> Executando etapa: Agregação Gold UF/Mês...")
        ca_uf_mes_gold(anos=anos)
        logger.info("-> Executando etapa: Agregação Gold Município/Mês...")
        ca_municipio_mes_gold(anos=anos)

    end_time = datetime.now(tz=UTC)
    logger.info(f"Pipeline concluído com sucesso. Tempo total: {end_time - start_time}")


def main() -> None:
    parsed = parse_arguments(sys.argv[1:])
    run_pipeline(
        steps=parsed.steps,
        ano_inicio=parsed.ano_inicio,
        ano_fim=parsed.ano_fim,
    )


if __name__ == "__main__":
    main()
