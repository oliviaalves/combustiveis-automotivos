from combustiveis_automotivos.collect_data import ja_processado, montar_urls
from combustiveis_automotivos.config import ANO_FIM, ANO_INICIO


def test_montar_urls_default():
    """Testa se a montagem de URLs gera a lista completa de semestres por padrão."""
    urls = montar_urls()
    anos_esperados = (ANO_FIM - ANO_INICIO + 1) * 2
    assert len(urls) == anos_esperados

    # Verifica exceção conhecida (2022-S1)
    excecao = [u for u in urls if u[0] == 2022 and u[1] == 1]
    assert len(excecao) == 1
    assert excecao[0][3] == "precos-semestrais-ca.zip"

    # Verifica formato padrão pós-2022 (.zip)
    post_2022 = [u for u in urls if u[0] == 2023 and u[1] == 1]
    assert post_2022[0][3] == "ca-2023-01.zip"

    # Verifica formato pré-2022 (.csv)
    pre_2022 = [u for u in urls if u[0] == 2020 and u[1] == 2]
    assert pre_2022[0][3] == "ca-2020-02.csv"


def test_montar_urls_custom_range():
    """Testa montagem de URLs com intervalo de anos customizado."""
    urls = montar_urls(ano_inicio=2023, ano_fim=2024)
    assert len(urls) == 4
    assert [u[0] for u in urls] == [2023, 2023, 2024, 2024]
    assert [u[1] for u in urls] == [1, 2, 1, 2]
    assert all(u[3].endswith(".zip") for u in urls)


def test_ja_processado(tmp_path, monkeypatch):
    """Testa a detecção de arquivos já existentes na pasta processed."""
    monkeypatch.setattr("combustiveis_automotivos.collect_data.PROCESSED_DIR", tmp_path)

    assert not ja_processado("ca-2023-01.zip")

    # Cria arquivo falso na pasta processed
    fake_processed = tmp_path / "20260101_120000_ca-2023-01.zip"
    fake_processed.write_text("dummy")

    assert ja_processado("ca-2023-01.zip")
