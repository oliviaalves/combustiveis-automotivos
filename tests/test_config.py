from pathlib import Path

from combustiveis_automotivos.config import (
    ANO_FIM,
    ANO_INICIO,
    BASE_DIR,
    BASE_URL,
    DATA_DIR,
    DELTA_TARGET,
    EXCECOES,
    HEADERS,
    MUNICIPIO_MES_GOLD_TARGET,
    PROCESSED_DIR,
    SILVER_TARGET,
    UF_MES_GOLD_TARGET,
)


def test_paths_resolution():
    """Valida se os caminhos no config.py são instâncias válidas de Path e apontam para a raiz."""
    assert isinstance(BASE_DIR, Path)
    assert (BASE_DIR / "pyproject.toml").exists()

    assert DATA_DIR == BASE_DIR / "data"
    assert PROCESSED_DIR == DATA_DIR / "processed"
    assert DELTA_TARGET == DATA_DIR / "output" / "delta" / "combustiveis_automotivos_raw"
    assert SILVER_TARGET == DATA_DIR / "output" / "delta" / "combustiveis_automotivos_silver"
    assert UF_MES_GOLD_TARGET == DATA_DIR / "output" / "delta" / "combustiveis_automotivos_uf_mes_gold"
    assert MUNICIPIO_MES_GOLD_TARGET == DATA_DIR / "output" / "delta" / "combustiveis_automotivos_municipio_mes_gold"


def test_config_constants():
    """Valida constantes essenciais de scraping e parâmetros temporais."""
    assert ANO_INICIO <= ANO_FIM
    assert BASE_URL.startswith("https://")
    assert (2022, 1) in EXCECOES
    assert "User-Agent" in HEADERS
