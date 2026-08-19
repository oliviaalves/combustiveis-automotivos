"""
Baixa os arquivos "Combustíveis Automotivos" da Série Histórica de Preços de
Combustíveis, direto do site da ANP (gov.br), sem precisar de API/chave.

Fonte: https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis
"""

import logging
import os
import time
from pathlib import Path

import requests
from tqdm import tqdm

from combustiveis_automotivos.config import (
    ANO_FIM,
    ANO_INICIO,
    BASE_URL,
    DATA_DIR,
    ESPERA_BASE_SEGUNDOS,
    EXCECOES,
    HEADERS,
    MAX_TENTATIVAS,
    PROCESSED_DIR,
)

logger = logging.getLogger(__name__)


def montar_urls(
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
) -> list[tuple[int, int, str, str]]:
    """
    Monta a lista de URLs para baixar os arquivos da ANP, de acordo com o padrão
    de nomenclatura dos arquivos e as exceções conhecidas.
    Retorna uma lista de tuplas (ano, semestre, url, nome_arquivo).
    """
    inicio = ano_inicio if ano_inicio is not None else ANO_INICIO
    fim = ano_fim if ano_fim is not None else ANO_FIM

    urls = []
    for ano in range(inicio, fim + 1):
        for semestre in (1, 2):
            if (ano, semestre) in EXCECOES:
                nome_arquivo = EXCECOES[(ano, semestre)]
            elif ano >= 2022:
                nome_arquivo = f"ca-{ano}-{semestre:02d}.zip"
            else:
                nome_arquivo = f"ca-{ano}-{semestre:02d}.csv"

            url = f"{BASE_URL}/{nome_arquivo}"
            urls.append((ano, semestre, url, nome_arquivo))
    return urls


def baixar_arquivo(url: str, caminho_final: Path) -> bool:
    """
    Baixa um arquivo da ANP, com suporte a retomada de download e tratamento de
    exceções. Retorna True se o download foi bem-sucedido, False caso contrário.
    """
    caminho_tmp = caminho_final.with_suffix(caminho_final.suffix + ".tmp")

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            bytes_ja_baixados = caminho_tmp.stat().st_size if caminho_tmp.exists() else 0
            headers = dict(HEADERS)
            modo_arquivo = "wb"

            if bytes_ja_baixados > 0:
                headers["Range"] = f"bytes={bytes_ja_baixados}-"
                modo_arquivo = "ab"

            with requests.get(url, headers=headers, stream=True, timeout=(10, 60)) as resp:
                if resp.status_code == 404:
                    logger.warning(
                        f"[NÃO ENCONTRADO] {caminho_final.name} (404) — pode não existir para esse período"
                    )
                    return False

                # Servidor não suporta retomada (ignorou o Range) -> recomeça do zero
                if bytes_ja_baixados > 0 and resp.status_code != 206:
                    logger.info("[ERRO] servidor não suportou retomada, reiniciando do zero...")
                    bytes_ja_baixados = 0
                    modo_arquivo = "wb"

                resp.raise_for_status()

                total_no_header = int(resp.headers.get("Content-Length", 0))
                total = (bytes_ja_baixados + total_no_header) if total_no_header > 0 else None

                with open(caminho_tmp, modo_arquivo) as f, tqdm(
                    total=total,
                    initial=bytes_ja_baixados,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=f"    {caminho_final.name}",
                    leave=False,
                ) as barra:
                    for chunk in resp.iter_content(chunk_size=1024 * 256):
                        f.write(chunk)
                        barra.update(len(chunk))

            os.replace(caminho_tmp, caminho_final)
            return True

        except requests.RequestException as e:
            logger.warning(f"    [tentativa {tentativa}/{MAX_TENTATIVAS}] falhou: {e}")

            if tentativa < MAX_TENTATIVAS:
                espera = ESPERA_BASE_SEGUNDOS * (2 ** (tentativa - 1))
                logger.info(f"    aguardando {espera}s antes de tentar de novo...")
                time.sleep(espera)
            else:
                logger.error(f"    [DESISTINDO] {caminho_final.name} após {MAX_TENTATIVAS} tentativas")
                return False

    return False


def ja_processado(nome_arquivo: str) -> bool:
    """
    Verifica se já existe na pasta processed um arquivo terminando em
    "_<nome_arquivo>" para saber se o arquivo já foi processado.
    """
    if not PROCESSED_DIR.exists():
        return False

    encontrados = list(PROCESSED_DIR.glob(f"*_{nome_arquivo}"))
    return bool(encontrados)


def collect_data(
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
) -> None:
    """Baixa os arquivos da ANP, respeitando o padrão de nomenclatura e as exceções."""
    os.makedirs(DATA_DIR, exist_ok=True)
    urls = montar_urls(ano_inicio=ano_inicio, ano_fim=ano_fim)
    falharam = []

    for ano, semestre, url, nome_arquivo in urls:
        caminho = DATA_DIR / nome_arquivo

        if caminho.exists():
            logger.info(f"[JÁ EXISTE em data] {nome_arquivo}")
            continue

        if ja_processado(nome_arquivo):
            logger.info(f"[JÁ PROCESSADO] {nome_arquivo} (encontrado em processed)")
            continue

        logger.info(f"[BAIXANDO] {ano} - {semestre}º sem. -> {url}")
        sucesso = baixar_arquivo(url, caminho)

        if sucesso:
            logger.info(f"    salvo em: {caminho}")
        else:
            falharam.append(nome_arquivo)

        time.sleep(5)  # gentileza com o servidor

    logger.info("Coleta concluída.")
    if falharam:
        logger.warning(f"Arquivos que não foi possível baixar ({len(falharam)}):")
        for nome in falharam:
            logger.warning(f"  - {nome}")


if __name__ == "__main__":
    collect_data()