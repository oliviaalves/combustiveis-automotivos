"""
Configurações globais e caminhos do projeto combustiveis_automotivos.
"""

from pathlib import Path

# Diretórios base resolvidos dinamicamente a partir do diretório raiz do projeto
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "output" / "delta"

# Alvos das tabelas Delta Lake (Camadas Bronze/Raw, Silver e Gold)
DELTA_TARGET = OUTPUT_DIR / "combustiveis_automotivos_raw"
SILVER_TARGET = OUTPUT_DIR / "combustiveis_automotivos_silver"
UF_MES_GOLD_TARGET = OUTPUT_DIR / "combustiveis_automotivos_uf_mes_gold"
MUNICIPIO_MES_GOLD_TARGET = OUTPUT_DIR / "combustiveis_automotivos_municipio_mes_gold"

# Parâmetros para coleta de dados da ANP
BASE_URL = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsas/ca"
ANO_INICIO = 2004
ANO_FIM = 2026
INFLACAO_DF = DATA_DIR / "inflacao_anual.json"
EXCECOES = {
    (2022, 1): "precos-semestrais-ca.zip",
}
MAX_TENTATIVAS = 5
ESPERA_BASE_SEGUNDOS = 3
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}
