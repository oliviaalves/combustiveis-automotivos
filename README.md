# Combustíveis Automotivos - Pipeline de Dados ANP

Este projeto consiste em um pipeline de ETL de dados da **Série Histórica de Preços de Combustíveis Automotivos** fornecidos pela ANP (Agência Nacional do Petróleo, Gás Natural e Biocombustíveis).

A arquitetura adota o padrão **Medallion Architecture** (Raw / Silver / Gold) utilizando **Polars** para processamento performático em memória e **Delta Lake** como formato de armazenamento colunar com suporte a particionamento.

---

## 🏗 Arquitetura dos Dados

1. **Ingestão (Scraping)**: Download resiliente com retentativas e suporte a retomada parcial dos arquivos `.csv` e `.zip` disponibilizados no portal de dados abertos da ANP.
2. **Bronze / Raw (`data/output/delta/combustiveis_automotivos_raw`)**: Consolidação incremental arquivo a arquivo (prevenindo OOM) com preservação de tipos originais (ex.: zeros à esquerda em CNPJ/CEP).
3. **Silver (`data/output/delta/combustiveis_automotivos_silver`)**: Limpeza, padronização de tipos de dados (conversão de datas e valores numéricos com vírgula), desduplicação por chaves primárias e particionamento por `Ano_de_coleta`.
4. **Gold (`data/output/delta/...`)**:
   - `combustiveis_automotivos_uf_mes_gold`: Agregações mensais por estado (UF) e tipo de produto (preço médio, máximo e mínimo), particionada por `Ano_de_coleta`.
   - `combustiveis_automotivos_municipio_mes_gold`: Agregações mensais por município e estado, particionada por `Ano_de_coleta`.

---

## 📁 Estrutura do Projeto

```text
combustiveis_automotivos/
├── pyproject.toml                     # Gerenciamento de dependências (uv) e metadados
├── README.md                          # Documentação do projeto
├── notebooks/                         # Notebooks exploratórios e análises
│   ├── silver.ipynb
│   └── gold.ipynb
├── src/
│   └── combustiveis_automotivos/      # Pacote Python principal
│       ├── __init__.py
│       ├── config.py                  # Configurações globais e resolução de caminhos
│       ├── collect_data.py            # Coleta e download de dados da ANP
│       ├── parse_data.py              # Ingestão para camada Raw Delta
│       ├── generate_silver.py         # Transformação e limpeza para camada Silver
│       ├── gold_transformations.py    # Regras puras de agregação da camada Gold
│       ├── generate_gold_uf.py        # Agregação Gold UF/Mês
│       ├── generate_gold_mcp.py       # Agregação Gold Município/Mês
│       └── main.py                    # CLI e orquestração do pipeline
└── tests/                             # Suíte de testes automatizados (pytest)
    ├── test_cli.py
    ├── test_collect.py
    ├── test_config.py
    ├── test_parse.py
    └── test_transformations.py
```

---

## 🚀 Como Executar

### Pré-requisitos
- Python `>= 3.11`
- Gerenciador [uv](https://github.com/astral-sh/uv)

### Instalação
Sincronize as dependências e o ambiente virtual:
```bash
uv sync
```

### Executando o Pipeline Completo
Execute a pipeline através do comando registrado no CLI:
```bash
uv run combustiveis-automotivos
```

### Execução Customizada (CLI Flags)
Você pode selecionar etapas específicas e limitar o intervalo de anos coletados:
```bash
# Executar apenas a transformação Silver e agregações Gold:
uv run combustiveis-automotivos --steps silver gold

# Executar apenas a coleta para os anos de 2023 a 2024:
uv run combustiveis-automotivos --steps collect --ano-inicio 2023 --ano-fim 2024
```

### Executando a Suíte de Testes
```bash
uv run pytest -v
```

---

## 📊 Dashboard Interativo (Streamlit)

Para inicializar o painel interativo de análise de margens e comparativos:
```bash
uv run streamlit run app.py
```

