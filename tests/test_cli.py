from unittest.mock import patch

import pytest

from combustiveis_automotivos.main import parse_arguments, run_pipeline


def test_parse_arguments_default():
    """Testa valores padrão de argumentos do CLI."""
    args = parse_arguments([])
    assert args.steps == ["collect", "parse", "silver", "gold"]
    assert args.ano_inicio is None
    assert args.ano_fim is None


def test_parse_arguments_custom():
    """Testa passagem de flags customizadas."""
    args = parse_arguments(["--steps", "silver", "gold", "--ano-inicio", "2023", "--ano-fim", "2024"])
    assert args.steps == ["silver", "gold"]
    assert args.ano_inicio == 2023
    assert args.ano_fim == 2024


def test_parse_arguments_invalid_step():
    """Testa erro ao passar etapa desconhecida."""
    with pytest.raises(SystemExit):
        parse_arguments(["--steps", "etapa_inexistente"])


def test_run_pipeline_selective_execution():
    """Valida se run_pipeline chama exclusivamente as funções das etapas selecionadas com suporte a anos."""
    with (
        patch("combustiveis_automotivos.main.collect_data") as mock_collect,
        patch("combustiveis_automotivos.main.parse_data") as mock_parse,
        patch("combustiveis_automotivos.main.generate_silver") as mock_silver,
        patch("combustiveis_automotivos.main.ca_uf_mes_gold") as mock_gold_uf,
        patch("combustiveis_automotivos.main.ca_municipio_mes_gold") as mock_gold_mcp,
    ):
        # Executa apenas silver e gold para 2023 e 2024
        run_pipeline(steps=["silver", "gold"], ano_inicio=2023, ano_fim=2024)

        mock_collect.assert_not_called()
        mock_parse.assert_not_called()
        mock_silver.assert_called_once_with(anos=[2023, 2024])
        mock_gold_uf.assert_called_once_with(anos=[2023, 2024])
        mock_gold_mcp.assert_called_once_with(anos=[2023, 2024])
