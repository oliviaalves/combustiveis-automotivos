import io
import logging
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from combustiveis_automotivos.config import DATA_DIR, DELTA_TARGET, PROCESSED_DIR

logger = logging.getLogger(__name__)


def _extrair_csv_de_zip(origem: Path | bytes | io.BytesIO) -> bytes:
    """
    Abre um .zip e retorna os bytes do primeiro .csv encontrado dentro dele.
    Se houver mais de um .csv ou nenhum, levanta ValueError.
    """
    buffer = io.BytesIO(origem) if isinstance(origem, bytes) else origem
    with zipfile.ZipFile(buffer) as zf:
        nomes_csv = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not nomes_csv:
            raise ValueError(f"Nenhum .csv encontrado dentro do arquivo ZIP {origem}")
        if len(nomes_csv) > 1:
            raise ValueError(
                f"O arquivo ZIP contém múltiplos CSVs: {nomes_csv} — decida qual usar."
            )
        with zf.open(nomes_csv[0]) as f:
            return f.read()


def _ler_csv(origem: Path | str | bytes | io.BytesIO, is_zip: bool = False, **kwargs) -> pl.DataFrame:
    """
    Lê um .csv ou .zip (contendo um .csv) da ANP, lidando com encodings e tipos de colunas.
    """
    if isinstance(origem, (Path, str)):
        caminho = Path(origem)
        if caminho.suffix.lower() == ".zip":
            conteudo_bytes = _extrair_csv_de_zip(caminho)
        else:
            conteudo_bytes = caminho.read_bytes()
    elif isinstance(origem, bytes):
        if is_zip:
            conteudo_bytes = _extrair_csv_de_zip(origem)
        else:
            conteudo_bytes = origem
    elif isinstance(origem, io.BytesIO):
        if is_zip:
            conteudo_bytes = _extrair_csv_de_zip(origem)
        else:
            conteudo_bytes = origem.getvalue()
    else:
        raise TypeError(f"Tipo não suportado para leitura de CSV: {type(origem)}")

    try:
        texto = conteudo_bytes.decode("utf-8")
    except UnicodeDecodeError:
        texto = conteudo_bytes.decode("latin-1")

    buffer = io.BytesIO(texto.encode("utf-8"))
    
    # Configurações padrão de leitura de CSV da ANP
    csv_kwargs = {
        "has_header": True,
        "separator": ";",
        "null_values": ["NULL", "S/N."],
        "infer_schema_length": 10000,
    }
    csv_kwargs.update(kwargs)

    # Identifica colunas no header e aplica Utf8 a todas as colunas de texto/endereço/cadastro
    header_line = texto.split("\n", 1)[0] if texto else ""
    sep = csv_kwargs.get("separator", ";")
    header_cols = [c.strip().strip('"').strip("'") for c in header_line.split(sep)]
    schema_overrides = {
        col: pl.Utf8
        for col in header_cols
        if any(termo in col.lower() for termo in (
            "cnpj", "cep", "numero", "rua", "complemento", "bairro", "revenda",
            "bandeira", "regiao", "estado", "municipio", "produto", "unidade", "data"
        ))
    }
    
    # Mescla com schema_overrides passados via kwargs se houver
    if "schema_overrides" in csv_kwargs:
        schema_overrides.update(csv_kwargs.pop("schema_overrides"))

    df = pl.read_csv(buffer, schema_overrides=schema_overrides, **csv_kwargs)
    return df


def parse_data() -> None:
    """
    Lê os arquivos .csv e .zip da ANP na pasta DATA_DIR iterativamente, gravando
    na camada raw Delta (DELTA_TARGET) e movendo cada arquivo para PROCESSED_DIR
    imediatamente após a gravação bem-sucedida, prevenindo alto consumo de memória (OOM).
    """
    files = sorted(DATA_DIR.glob("*.csv")) + sorted(DATA_DIR.glob("*.zip"))

    if not files:
        logger.info("Nenhum arquivo CSV/ZIP encontrado para processar.")
        return

    DELTA_TARGET.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    for file in files:
        logger.info(f"Processando: {file.name}...")
        try:
            df = _ler_csv(file)
            df.write_delta(
                target=str(DELTA_TARGET),
                mode="append",
                delta_write_options={"schema_mode": "merge"},
            )
            
            timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
            destino = PROCESSED_DIR / f"{timestamp}_{file.name}"
            shutil.move(str(file), str(destino))
            logger.info(f"Gravado no Delta e movido: {file.name} -> {destino.name}")

        except Exception as e:
            logger.exception(f"Erro ao processar o arquivo {file.name}")
            raise e
