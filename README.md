# Sistema de Rebalanceamento de Carteira

Motor analítico com interface interativa para rebalanceamento de carteira multi-classe (ações, FIIs, crypto, Tesouro Direto, renda fixa privada).

## Funcionalidades

- **Rebalanceamento em 2 camadas**: primeiro equaliza classes de ativo, depois ativos individuais dentro de cada classe
- **Zonas cinzentas**: bandas de tolerância relativas + absolutas determinam BUY / HOLD / SELL
- **Markowitz**: fronteira eficiente com blend configurável entre pesos atuais e ótimos
- **Reserva de emergência**: meta vs realizado com gauge visual e composição detalhada
- **Alocação de capital**: split inteligente entre reserva e investimentos
- **27 posições**: ações BR, FIIs, crypto (USDT/ALAB), Tesouro Direto, CDBs, LCAs, CRIs
- **Pricing multi-fonte**: brapi.dev (ações/FIIs B3) + yfinance (histórico + crypto) + API Tesouro Direto

## Setup

```bash
# Clonar e instalar
git clone https://github.com/JoaoToni12/analise-investimentos.git
cd analise-investimentos
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements-dev.txt

# Configurar token brapi.dev
cp .env.example .env
# Edite .env e insira seu BRAPI_TOKEN (cadastro gratuito em https://brapi.dev)

# Rodar
streamlit run main.py
```

## Comandos úteis

```bash
make test          # Rodar testes completos com coverage
make test-fast     # Testes rápidos (exclui lentos)
make lint          # Lint + format (ruff)
make type-check    # Type check (mypy)
make run           # Iniciar Streamlit
make docker-build  # Build da imagem Docker
```

## Arquitetura

```
/ingestion   Comunicação com APIs externas (brapi, yfinance, MCP, Tesouro)
/engine      Núcleo matemático puro (Markowitz, zonas cinzentas, rebalancer)
/ui          Componentes Streamlit + Plotly
/tests       81 testes automatizados, 82% coverage
```

## Segurança

- Zero credenciais no código — `.env` + `python-dotenv`
- `.env` em `.gitignore` e `.cursorignore`
- Privacy Mode recomendado no Cursor
- MCP com aprovação manual por chamada

## Tech Stack

Python 3.10+ | Streamlit | Plotly | Pandas | NumPy | SciPy | yfinance | brapi.dev
