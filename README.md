<div align="center">

<img src="frontend/favicon.svg" alt="Marca Lynx" width="96" height="96">

# Lynx

**E-commerce demonstrativo** com catálogo, contas de cliente e vendedor, sacola e pedidos.

Interface web responsiva + API FastAPI + Redis Cloud.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Redis](https://img.shields.io/badge/Data-Redis-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![JavaScript](https://img.shields.io/badge/Frontend-JavaScript-F7DF1E?logo=javascript&logoColor=222222)](https://developer.mozilla.org/docs/Web/JavaScript)
[![Testes](https://img.shields.io/badge/Testes-pytest-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)

</div>

> [!NOTE]
> O checkout é **acadêmico**: registra o pedido e atualiza o estoque, mas não processa pagamentos.

---

## Sumário

- [Sobre o projeto](#sobre-o-projeto)
- [Início rápido](#início-rápido)
- [Funcionalidades](#funcionalidades)
- [Perfis e permissões](#perfis-e-permissões)
- [Tecnologias](#tecnologias)
- [Arquitetura](#arquitetura)
- [Instalação e configuração](#instalação-e-configuração)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Execução](#execução)
- [Redis e persistência](#redis-e-persistência)
- [Testes](#testes)
- [Documentação complementar](#documentação-complementar)
- [Limitações e próximos passos](#limitações-e-próximos-passos)

## Sobre o projeto

A Lynx é uma loja virtual demonstrativa para explorar fluxos comuns de e-commerce:

- **Clientes** descobrem produtos, mantêm uma sacola e acompanham pedidos.
- **Vendedores** organizam categorias e administram os próprios produtos.

A interface é servida pelo próprio backend. Não há framework de frontend nem serviço de frontend separado.

## Início rápido

Pré-requisitos: **Python 3.11+** e uma instância Redis de desenvolvimento (veja [Pré-requisitos](#pré-requisitos)).

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env        # edite com os dados do seu Redis
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

| Recurso | Endereço |
|---|---|
| Loja (interface web) | <http://127.0.0.1:8000> |
| Documentação interativa da API | <http://127.0.0.1:8000/docs> |
| Estado do serviço | <http://127.0.0.1:8000/health> |

> No Windows, basta executar `iniciar.bat` depois de configurar o `.env`.

## Funcionalidades

| Área | O que está disponível |
|---|---|
| **Catálogo** | Listagem pública com busca, filtro por categoria e página de detalhes responsiva |
| **Contas** | Cadastro e autenticação de clientes e vendedores; perfil pessoal editável |
| **Vendedor** | Dados comerciais da loja, categorias e produtos próprios |
| **Compras** | Sacola com ajuste de quantidades, checkout demonstrativo, histórico e cancelamento de pedidos |
| **Segurança** | Sessões revogáveis, proteção de rotas por perfil e senhas com hash Argon2id |
| **API** | Documentação gerada automaticamente pelo FastAPI |

## Perfis e permissões

| Perfil | Acesso |
|---|---|
| **Visitante** | Catálogo, busca, filtros e detalhes dos produtos. |
| **Cliente** | Tudo do visitante, mais sacola, checkout demonstrativo, consulta dos próprios pedidos e edição do próprio perfil. |
| **Vendedor** | Edição do próprio perfil e dados da loja; criação e gerenciamento das próprias categorias e produtos. |

> [!IMPORTANT]
> As permissões são verificadas **pela API**; ocultar ações na interface não é o mecanismo de autorização.
> Clientes não consultam pedidos de terceiros e vendedores não gerenciam produtos de outros vendedores.
> Produtos legados sem proprietário podem continuar visíveis quando ativos, mas não são editáveis por vendedores.

## Tecnologias

| Área | Tecnologia |
|---|---|
| Backend e API | Python, FastAPI, Pydantic |
| Servidor ASGI | Uvicorn |
| Persistência e sessões | Redis Cloud, `redis-py` assíncrono |
| Segurança de senha | Argon2id (`argon2-cffi`) |
| Frontend | HTML, CSS e JavaScript sem framework |
| Testes | `pytest` e `httpx` |

As dependências Python estão em [`requirements.txt`](requirements.txt).

## Arquitetura

O FastAPI serve os arquivos de `frontend/` na raiz (`/`) e expõe os endpoints da aplicação sob `/api/v1`.

```mermaid
flowchart LR
    B[Navegador<br/>HTML · CSS · JS] -->|/ e /api/v1| R[Rotas<br/>api/routes]
    R --> S[Serviços<br/>regras de aplicação]
    S --> P[Repositórios]
    P --> D[(Redis Cloud)]
```

<details>
<summary><strong>Estrutura de diretórios</strong></summary>

```text
.
├── backend/
│   ├── app/
│   │   ├── api/routes/       # Rotas de saúde, autenticação, catálogo e pedidos
│   │   ├── core/             # Configuração e autenticação
│   │   ├── db/               # Cliente e ciclo de vida do Redis
│   │   ├── repositories/     # Acesso e persistência Redis
│   │   ├── schemas/          # Modelos e validação de dados
│   │   ├── scripts/          # Inspeção Redis e provisionamento de vendedor
│   │   ├── services/         # Regras de aplicação
│   │   └── main.py           # Criação da API e montagem do frontend
│   └── tests/                # Testes unitários e de integração
├── docs/                     # Guias da API, Redis e demonstração
├── frontend/
│   ├── index.html            # Página e diálogos da loja
│   ├── styles.css            # Tema e layout responsivo
│   ├── app.js                # Interações e chamadas à API
│   └── favicon.svg           # Marca Lynx
├── .env.example              # Modelo sem credenciais reais
├── iniciar.bat               # Inicialização assistida no Windows
└── requirements.txt          # Dependências Python
```

</details>

## Pré-requisitos

- Python 3.11 ou superior.
- Acesso a uma instância Redis compatível e configurada para o projeto.
- Windows para usar `iniciar.bat`; em outros sistemas, use os comandos equivalentes de ambiente virtual e Uvicorn.

## Instalação e configuração

No PowerShell, na pasta raiz do projeto:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edite o `.env` com os dados da sua instância Redis de desenvolvimento ou teste.

> [!WARNING]
> Nunca compartilhe nem versione o arquivo `.env`.

<details>
<summary>O PowerShell bloqueou a ativação do ambiente virtual?</summary>

Abra um terminal que permita executar o script de ativação ou use diretamente o executável `.venv\Scripts\python.exe`.

</details>

## Variáveis de ambiente

Configure **uma** das opções de conexão abaixo. Não coloque credenciais reais neste README nem em arquivos versionados.

**Opção A — URL Redis**

```dotenv
REDIS_URL=redis://default:SENHA@HOST:PORTA
```

Substitua `SENHA`, `HOST` e `PORTA` pelos valores do serviço. Caracteres especiais na senha precisam estar codificados para URL.

**Opção B — campos separados** (usada quando `REDIS_URL` não está definida)

```dotenv
REDIS_HOST=seu-host-redis
REDIS_PORT=6379
REDIS_USERNAME=default
REDIS_PASSWORD=sua-senha
```

**Opções da aplicação**

| Variável | Padrão | Descrição |
|---|---:|---|
| `REDIS_KEY_PREFIX` | `ecommerce` | Namespace das chaves Redis da aplicação. |
| `AUTH_SESSION_TTL_SECONDS` | `604800` | Duração da sessão em segundos (sete dias). |
| `AUTH_COOKIE_SECURE` | `false` | Define se o cookie de sessão exige HTTPS. |

> [!CAUTION]
> A configuração atual conecta via `redis://` **sem TLS**, conforme o ambiente Redis Cloud Essentials Free usado no desenvolvimento. Use apenas dados fictícios nessa instância.
> Para produção, são necessários: suporte a TLS no cliente Redis, HTTPS, `AUTH_COOKIE_SECURE=true` e revisão completa da configuração de segurança.

## Execução

### Windows

Com o `.env` configurado, execute na raiz:

```bat
iniciar.bat
```

O script procura `.venv` ou `venv`, verifica Python e dependências, confirma a presença do `.env` e inicia a aplicação. Encerre o servidor com `Ctrl+C`.

### Manual (qualquer sistema)

Com o ambiente virtual ativado:

```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Ao iniciar, a aplicação testa a conexão com o Redis usando `PING`.

## Redis e persistência

O Redis é o banco principal da aplicação:

| Estrutura | Uso |
|---|---|
| **Hashes** | Usuários, produtos, categorias e pedidos |
| **Sets** | Índices e relações |
| **Strings com TTL** | Sessões |

- Senhas são persistidas como hashes Argon2id, e o token bruto da sessão **não** é armazenado como valor no Redis.
- Carrinhos expiram após sete dias sem atualização.
- O estoque **não** é reservado enquanto o produto está na sacola: a disponibilidade é revalidada atomicamente no checkout.
- O cancelamento de pedido confirmado devolve o estoque uma única vez.

Veja [docs/REDIS.md](docs/REDIS.md) para o inventário de chaves, campos e relacionamentos, e [docs/REDIS-COMANDOS.md](docs/REDIS-COMANDOS.md) para consultas no Redis CLI.

## Testes

Com as dependências instaladas e o `.env` apontando para uma instância Redis **dedicada a testes**:

```powershell
python -m pytest -q
```

A suíte cobre validação de schemas, conexão e persistência Redis, autenticação, autorização, perfis, produtos, categorias, carrinhos e pedidos.

> [!WARNING]
> Os testes de integração criam registros temporários e os removem ao final, mas execute-os somente em uma instância de teste, nunca contra dados de produção.
> Se o Redis não estiver configurado, os testes que dependem dele são ignorados conforme os fixtures.

## Documentação complementar

| Documento | Conteúdo |
|---|---|
| [Manual de execução e demonstração](docs/manual.md) | Passo a passo para rodar e demonstrar o sistema |
| [Referência da API](docs/api.md) | Endpoints e contratos |
| [Modelagem Redis completa](docs/REDIS.md) | Chaves, campos e relacionamentos |
| [Cola de comandos Redis](docs/REDIS-COMANDOS.md) | Consultas úteis no Redis CLI |
| [Resumo de modelagem Redis](docs/redis-model.md) | Visão rápida do modelo de dados |
| [Histórico de progresso](PROGRESSO.md) | Evolução do projeto |

