import polars as pl
import pytest

from combustiveis_automotivos.generate_silver import transform_silver
from combustiveis_automotivos.gold_transformations import aggregate_gold


@pytest.fixture
def mock_raw_df() -> pl.DataFrame:
    """Fixture com dados brutos simulados contendo duplicatas, vírgula decimal e datas em formato brasileiro."""
    return pl.DataFrame({
        "Estado - Sigla": ["SP", "SP", "SP", "RJ"],
        "Municipio": ["SAO PAULO", "SAO PAULO", "CAMPINAS", "NITEROI"],
        "Produto": ["GASOLINA", "GASOLINA", "ETANOL", "GASOLINA"],
        "Data da Coleta": ["15/03/2023", "15/03/2023", "20/04/2023", "10/05/2024"],
        "Valor de Venda": ["5,49", "5,49", "3,89", "5,79"],
        "Valor de Compra": ["4,80", "4,80", "3,20", "5,10"],
        "Unidade de Medida": ["R$ / litro", "R$ / litro", "R$ / litro", "R$ / litro"],
        "Bandeira": ["BRANCA", "BRANCA", "IPIRANGA", "SHELL"],
        "CNPJ da Revenda": ["11.111.111/0001-11", "11.111.111/0001-11", "22.222.222/0001-22", "33.333.333/0001-33"],
        "Regiao - Sigla": ["SE", "SE", "SE", "SE"],  # Coluna extra que deve ser descartada
    })


@pytest.fixture
def mock_inflacao_df() -> pl.DataFrame:
    """Fixture com dados de inflação simulados no formato JSON desaninhado."""
    return pl.DataFrame({
        "indice": ["IPCA"],
        "referencia": ["junho/2026"],
        "fatores": [{"2023": 2.0, "2024": 1.5}],
    })


@pytest.fixture
def mock_silver_df() -> pl.DataFrame:
    """Fixture com dados no formato da camada Silver."""
    return pl.DataFrame({
        "Estado_Sigla": ["SP", "SP", "SP", "RJ"],
        "Municipio": ["SAO PAULO", "SAO PAULO", "CAMPINAS", "NITEROI"],
        "Produto": ["GASOLINA", "GASOLINA", "GASOLINA", "GASOLINA"],
        "Ano_de_coleta": [2023, 2023, 2023, 2023],
        "Mes_de_coleta": [3, 3, 3, 3],
        "Valor_de_Venda": [5.00, 6.00, 7.00, 8.00],
        "Valor_de_Compra": [4.00, 4.50, 5.00, 6.00],
        "Valor_de_Venda_ajustado": [5.00, 6.00, 7.00, 8.00],
        "Valor_de_Compra_ajustado": [4.00, 4.50, 5.00, 6.00],
        "Unidade_de_Medida": ["R$ / litro", "R$ / litro", "R$ / litro", "R$ / litro"],
        "Bandeira": ["BRANCA", "SHELL", "IPIRANGA", "SHELL"],
        "CNPJ_da_Revenda": ["11.111.111/0001-11", "22.222.222/0001-22", "33.333.333/0001-33", "44.444.444/0001-44"],
    })


def test_transform_silver_schema_and_types(mock_raw_df, mock_inflacao_df):
    """Testa transformação da camada raw para silver (limpeza, conversão e ajuste de inflação)."""
    silver = transform_silver(mock_raw_df, mock_inflacao_df)

    # 4 linhas originais -> 1 duplicata exata de CNPJ/chaves -> deve resultar em 3 linhas
    assert len(silver) == 3

    # Colunas resultantes esperadas
    colunas_esperadas = {
        "Estado_Sigla",
        "Municipio",
        "Produto",
        "Bandeira",
        "CNPJ_da_Revenda",
        "Valor_de_Venda",
        "Valor_de_Compra",
        "Valor_de_Venda_ajustado",
        "Valor_de_Compra_ajustado",
        "Unidade_de_Medida",
        "Data_da_Coleta",
        "Ano_de_coleta",
        "Mes_de_coleta",
    }
    assert set(silver.columns) == colunas_esperadas

    # Validação de conversão numérica
    assert silver["Valor_de_Venda"].dtype == pl.Float64
    assert silver["Valor_de_Compra"].dtype == pl.Float64
    assert silver["Valor_de_Venda_ajustado"].dtype == pl.Float64
    assert silver["Valor_de_Compra_ajustado"].dtype == pl.Float64

    sp_row = silver.filter((pl.col("Municipio") == "SAO PAULO") & (pl.col("Produto") == "GASOLINA"))
    assert sp_row["Valor_de_Venda"][0] == 5.49
    assert sp_row["Valor_de_Compra"][0] == 4.80
    # Fator 2023 = 2.0
    assert pytest.approx(sp_row["Valor_de_Venda_ajustado"][0], 0.001) == 10.98
    assert pytest.approx(sp_row["Valor_de_Compra_ajustado"][0], 0.001) == 9.60

    # Validação de data e extração de ano/mês
    assert silver["Data_da_Coleta"].dtype == pl.Date
    assert sp_row["Ano_de_coleta"][0] == 2023
    assert sp_row["Mes_de_coleta"][0] == 3


def test_transform_silver_cnpj_preservation():
    """Valida que postos com CNPJs distintos na mesma cidade e data são ambos preservados."""
    raw = pl.DataFrame({
        "Estado - Sigla": ["SP", "SP"],
        "Municipio": ["SAO PAULO", "SAO PAULO"],
        "Produto": ["GASOLINA", "GASOLINA"],
        "Data da Coleta": ["15/03/2023", "15/03/2023"],
        "Valor de Venda": ["5,49", "5,59"],
        "Valor de Compra": ["4,80", "4,90"],
        "Unidade de Medida": ["R$ / litro", "R$ / litro"],
        "Bandeira": ["BRANCA", "BRANCA"],
        "CNPJ da Revenda": ["11.111.111/0001-11", "22.222.222/0001-22"],  # CNPJs diferentes
    })
    silver = transform_silver(raw)
    assert len(silver) == 2


def test_transform_silver_filters_null_dates_and_invalid_prices():
    """Valida descarte de registros com datas nulas/inválidas ou valores não positivos."""
    raw = pl.DataFrame({
        "Estado - Sigla": ["SP", "SP", "SP"],
        "Municipio": ["SAO PAULO", "SAO PAULO", "SAO PAULO"],
        "Produto": ["GASOLINA", "GASOLINA", "GASOLINA"],
        "Data da Coleta": ["15/03/2023", None, "15/03/2023"],
        "Valor de Venda": ["5,49", "5,49", "0,00"],  # linha 2: data nula, linha 3: valor zero
        "Valor de Compra": ["4,80", "4,80", "4,80"],
        "Unidade de Medida": ["R$ / litro", "R$ / litro", "R$ / litro"],
        "Bandeira": ["BRANCA", "BRANCA", "BRANCA"],
        "CNPJ da Revenda": ["11.111.111/0001-11", "22.222.222/0001-22", "33.333.333/0001-33"],
    })
    silver = transform_silver(raw)
    assert len(silver) == 1
    assert silver["CNPJ_da_Revenda"][0] == "11111111000111"


def test_transform_silver_without_inflation(mock_raw_df):
    """Testa transformação da camada raw para silver sem fornecer inflação."""
    silver = transform_silver(mock_raw_df)
    assert len(silver) == 3
    sp_row = silver.filter((pl.col("Municipio") == "SAO PAULO") & (pl.col("Produto") == "GASOLINA"))
    assert sp_row["Valor_de_Venda_ajustado"][0] == sp_row["Valor_de_Venda"][0]
    assert sp_row["Valor_de_Compra_ajustado"][0] == sp_row["Valor_de_Compra"][0]


def test_transform_silver_missing_columns():
    """Testa se erro informativo é lançado quando faltam colunas obrigatórias."""
    invalido = pl.DataFrame({"Estado - Sigla": ["SP"]})
    with pytest.raises(ValueError, match="Colunas obrigatórias ausentes"):
        transform_silver(invalido)


def test_aggregate_gold_uf(mock_silver_df):
    """Testa agregação no grão UF/Mês."""
    grain = ["Estado_Sigla", "Produto", "Ano_de_coleta", "Mes_de_coleta"]
    gold_uf = aggregate_gold(mock_silver_df, grain_cols=grain)

    # Devem existir 2 grupos: (SP, GASOLINA, 2023, 3) e (RJ, GASOLINA, 2023, 3)
    assert len(gold_uf) == 2

    sp_agg = gold_uf.filter(pl.col("Estado_Sigla") == "SP")
    # SP tem valores de venda 5.0, 6.0, 7.0 -> média = 6.0, min = 5.0, max = 7.0
    assert pytest.approx(sp_agg["Valor_de_Venda_medio"][0], 0.001) == 6.0
    assert sp_agg["Valor_de_Venda_min"][0] == 5.0
    assert sp_agg["Valor_de_Venda_max"][0] == 7.0

    # SP valores de compra 4.0, 4.5, 5.0 -> média = 4.5, min = 4.0, max = 5.0
    assert pytest.approx(sp_agg["Valor_de_Compra_medio"][0], 0.001) == 4.5
    assert sp_agg["Valor_de_Compra_min"][0] == 4.0
    assert sp_agg["Valor_de_Compra_max"][0] == 5.0

    # Margem média SP = 6.0 - 4.5 = 1.5
    assert pytest.approx(sp_agg["Margem_media"][0], 0.001) == 1.5


def test_aggregate_gold_municipio(mock_silver_df):
    """Testa agregação no grão Município/Mês."""
    grain = ["Estado_Sigla", "Municipio", "Produto", "Ano_de_coleta", "Mes_de_coleta"]
    gold_mcp = aggregate_gold(mock_silver_df, grain_cols=grain)

    # 3 municípios: SAO PAULO (2 registros), CAMPINAS (1), NITEROI (1)
    assert len(gold_mcp) == 3

    sp_mcp = gold_mcp.filter(pl.col("Municipio") == "SAO PAULO")
    # Valores de venda para SAO PAULO: 5.0 e 6.0 -> média 5.5, min 5.0, max 6.0
    assert pytest.approx(sp_mcp["Valor_de_Venda_medio"][0], 0.001) == 5.5
    assert sp_mcp["Valor_de_Venda_min"][0] == 5.0
    assert sp_mcp["Valor_de_Venda_max"][0] == 6.0

    # Valores de compra para SAO PAULO: 4.0 e 4.5 -> média 4.25
    assert pytest.approx(sp_mcp["Valor_de_Compra_medio"][0], 0.001) == 4.25
    assert pytest.approx(sp_mcp["Margem_media"][0], 0.001) == 1.25


def test_build_gold_layer_with_partition_preservation(mock_silver_df, tmp_path):
    """Testa a geração da camada Gold e a preservação de partições antigas ao rodar com filtro de anos."""
    from combustiveis_automotivos.gold_transformations import build_gold_layer

    source_dir = tmp_path / "silver"
    target_dir = tmp_path / "gold"

    # Cria tabela silver inicial com anos 2023 e 2024
    df_2024 = mock_silver_df.with_columns(
        Ano_de_coleta=pl.lit(2024, dtype=mock_silver_df["Ano_de_coleta"].dtype),
        Valor_de_Venda_ajustado=pl.lit(10.0),
        Valor_de_Compra_ajustado=pl.lit(8.0),
    )
    full_silver = pl.concat([mock_silver_df, df_2024])
    full_silver.write_delta(
        str(source_dir),
        mode="overwrite",
        delta_write_options={"partition_by": ["Ano_de_coleta"]},
    )

    grain = ["Estado_Sigla", "Produto", "Ano_de_coleta", "Mes_de_coleta"]

    # 1. Primeira execução: gera para todos os anos
    build_gold_layer(source_target=source_dir, output_target=target_dir, grain_cols=grain)
    gold_res1 = pl.read_delta(str(target_dir))
    assert set(gold_res1["Ano_de_coleta"].to_list()) == {2023, 2024}

    # 2. Segunda execução seletiva apenas para 2024: deve sobrescrever 2024 mas preservar 2023
    build_gold_layer(
        source_target=source_dir,
        output_target=target_dir,
        grain_cols=grain,
        anos=[2024],
    )
    gold_res2 = pl.read_delta(str(target_dir))
    assert set(gold_res2["Ano_de_coleta"].to_list()) == {2023, 2024}
