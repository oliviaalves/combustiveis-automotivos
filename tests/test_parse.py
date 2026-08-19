import io
import zipfile
from pathlib import Path

import pytest

from combustiveis_automotivos.parse_data import _extrair_csv_de_zip, _ler_csv


def _criar_zip_em_memoria(arquivos: dict[str, str | bytes]) -> bytes:
    """Helper para gerar arquivo ZIP em memória."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for nome, conteudo in arquivos.items():
            if isinstance(conteudo, str):
                conteudo = conteudo.encode("utf-8")
            zf.writestr(nome, conteudo)
    return buf.getvalue()


def test_extrair_csv_de_zip_valido():
    """Testa extração de CSV único dentro de um ZIP."""
    csv_content = "col1;col2\nval1;val2"
    zip_bytes = _criar_zip_em_memoria({"dados.csv": csv_content})

    extraido = _extrair_csv_de_zip(zip_bytes)
    assert extraido.decode("utf-8") == csv_content


def test_extrair_csv_de_zip_sem_csv():
    """Testa falha quando o ZIP não contém nenhum CSV."""
    zip_bytes = _criar_zip_em_memoria({"readme.txt": "sem csv aqui"})
    with pytest.raises(ValueError, match="Nenhum .csv encontrado"):
        _extrair_csv_de_zip(zip_bytes)


def test_extrair_csv_de_zip_multiplos_csvs():
    """Testa falha quando o ZIP contém múltiplos CSVs."""
    zip_bytes = _criar_zip_em_memoria({
        "arquivo1.csv": "a;b",
        "arquivo2.csv": "c;d",
    })
    with pytest.raises(ValueError, match="múltiplos CSVs"):
        _extrair_csv_de_zip(zip_bytes)


def test_ler_csv_utf8():
    """Testa leitura de CSV com encoding UTF-8."""
    conteudo = "Região - Sigla;Estado - Sigla;Municipio\nSE;SP;São Paulo"
    df = _ler_csv(conteudo.encode("utf-8"))
    assert df.shape == (1, 3)
    assert df["Municipio"][0] == "São Paulo"


def test_ler_csv_latin1_fallback():
    """Testa leitura de CSV com caracteres especiais em Latin-1 (fallback automático)."""
    conteudo_latin1 = "Região - Sigla;Estado - Sigla;Municipio\nNE;CE;Crateús".encode("latin-1")
    df = _ler_csv(conteudo_latin1)
    assert df.shape == (1, 3)
    assert df["Municipio"][0] == "Crateús"


def test_ler_csv_cnpj_cep_como_texto():
    """Testa se colunas com 'cnpj' e 'cep' são mantidas como String/Utf8."""
    conteudo = "CNPJ da Revenda;CEP;Valor\n00111222000199;01001000;5.99"
    df = _ler_csv(conteudo.encode("utf-8"))
    assert df.schema["CNPJ da Revenda"] == df.schema["CEP"]
    assert str(df["CNPJ da Revenda"].dtype).lower().startswith("str") or str(df["CNPJ da Revenda"].dtype).lower().startswith("utf8")
    assert df["CNPJ da Revenda"][0] == "00111222000199"
    assert df["CEP"][0] == "01001000"


def test_ler_csv_a_partir_de_zip():
    """Testa _ler_csv passando bytes de ZIP com flag is_zip=True."""
    csv_raw = "Estado - Sigla;Municipio;Produto\nRJ;Niterói;GASOLINA"
    zip_bytes = _criar_zip_em_memoria({"ca-2023-01.csv": csv_raw})
    df = _ler_csv(zip_bytes, is_zip=True)
    assert df.shape == (1, 3)
    assert df["Produto"][0] == "GASOLINA"
