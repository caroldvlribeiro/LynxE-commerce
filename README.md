<div align="center">

<img src="frontend/favicon.svg" alt="Marca Lynx" width="96" height="96" />

# 🛍️🐾 Lynx

### E-commerce demonstrativo em **FastAPI + Redis + JavaScript**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![Redis](https://img.shields.io/badge/Redis_Cloud-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=222222)
![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)

🏬 **Catálogo**  •  🛒 **Sacola**  •  📦 **Pedidos**  •  🔐 **Sessões e perfis**

*Interface web responsiva + API documentada automaticamente*

</div>

> [!IMPORTANT]
> 🎓 O checkout é **acadêmico**: registra o pedido e atualiza o estoque, mas **não processa pagamentos**.

---

## 📌 Sobre o projeto

A Lynx é uma loja virtual demonstrativa para explorar os fluxos mais comuns de um e-commerce:

- 🛒 **Clientes** descobrem produtos, mantêm uma sacola e acompanham pedidos.
- 🏪 **Vendedores** organizam categorias e administram os próprios produtos.

A interface é **servida pelo próprio backend**: não há framework de frontend nem serviço de frontend separado.

|              | 🖥️ Frontend                    | ⚙️ Backend                          |
|--------------|-------------------------------|------------------------------------|
| **Stack**    | HTML, CSS e JavaScript puros  | Python, FastAPI e Pydantic         |
| **Acesso**   | `/`                           | `/api/v1`                          |
| **Dados**    | Consome a API                 | Redis Cloud (`redis-py` assíncrono)|
| **Destaque** | Layout responsivo             | Autorização por perfil na API      |

---

## ✨ Funcionalidades

| 🛍️ Compra | 👤 Contas | 🏪 Loja | 🔒 Plataforma |
|---|---|---|---|
| Catálogo público | Cadastro de clientes e vendedores | Categorias próprias | API documentada (`/docs`) |
| Busca e filtro por categoria | Autenticação | Produtos próprios | Sessões revogáveis |
| Detalhes do produto | Perfil pessoal | Dados comerciais da loja | Rotas protegidas por perfil |
| Sacola com ajuste de quantidades | | | Senhas com **Argon2id** |
| Checkout, histórico e cancelamento | | | |

---

## 🔐 Perfis e permissões

| Perfil | Acesso |
|---|---|
| 👤 **Visitante** | Catálogo, busca, filtros e detalhes dos produtos. |
| 🛒 **Cliente** | Recursos de visitante + sacola, checkout demonstrativo, consulta dos próprios pedidos e edição do próprio perfil. |
| 🏪 **Vendedor** | Edição do próprio perfil e dados da loja; criação e gerenciamento das próprias categorias e produtos. |

> 🛡️ As permissões são verificadas **pela API**; ocultar ações na interface **não** é o mecanismo de autorização.
> Clientes não consultam pedidos de terceiros, e vendedores não gerenciam produtos de outros vendedores.

> 📎 **Produtos legados** sem proprietário podem continuar visíveis quando ativos, mas não são editáveis por vendedores.

---

## 🛠️ Tecnologias

| Tecnologia | Uso |
|---|---|
| 🐍 **Python 3.11+** | Linguagem |
| ⚡ **FastAPI** | Framework da API |
| 🧩 **Pydantic** | Modelos e validação de dados |
| 🦄 **Uvicorn** | Servidor ASGI |
| 🟥 **Redis Cloud** | Persistência e sessões |
| 🔌 **redis-py (async)** | Cliente Redis assíncrono |
| 🔑 **argon2-cffi** | Hash de senhas (Argon2id) |
| 🟨 **HTML, CSS e JS** | Frontend sem framework |
| 🧪 **pytest + httpx** | Testes |

As dependências estão em [`requirements.txt`](requirements.txt).

---

## 🏗️ Arquitetura

```mermaid
flowchart LR
    A[🌐 Navegador<br/>HTML · CSS · JS] -->|/api/v1| B[🛣️ Rotas]
    B --> C[⚙️ Services]
    C --> D[🗃️ Repositories]
    D --> E[(🟥 Redis Cloud)]
    B -.->|valida com| F[🧩 Schemas<br/>Pydantic]
    G[🚀 main.py] -->|serve / | A
```

| Camada | Pasta | Papel |
|---|---|---|
| 🟦 **Rotas** | `api/routes/` | Saúde, autenticação, catálogo e pedidos |
| 🟪 **Services** | `services/` | Regras de aplicação |
| 🟥 **Repositories** | `repositories/` | Acesso e persistência no Redis |
| 🟩 **Schemas** | `schemas/` | Modelos e validação de dados |
| 🟧 **Core** | `core/` | Configuração e autenticação |
| ⬛ **DB** | `db/` | Cliente e ciclo de vida do Redis |

### 📁 Estrutura de pastas

```text
.
├── 🐍 backend/
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
├── 📚 docs/                  # Guias da API, Redis e demonstração
├── 🌐 frontend/
│   ├── index.html            # Página e diálogos da loja
│   ├── styles.css            # Tema e layout responsivo
│   ├── app.js                # Interações e chamadas à API
│   └── favicon.svg           # Marca Lynx
├── 🔧 .env.example           # Modelo sem credenciais reais
├── 🪟 iniciar.bat            # Inicialização assistida no Windows
└── 📦 requirements.txt       # Dependências Python
```

---

## 🚀 Como executar

**Pré-requisitos:** Python 3.11+ e acesso a uma instância Redis compatível. Para usar o `iniciar.bat` é preciso Windows; nos outros sistemas, use os comandos manuais.

**1️⃣ Crie o ambiente virtual e instale as dependências** (PowerShell, na raiz do projeto)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

**2️⃣ Crie o `.env`**

```powershell
Copy-Item .env.example .env
```

Edite-o com os dados da sua instância Redis de desenvolvimento ou teste (veja [Variáveis de ambiente](#-variáveis-de-ambiente)).

**3️⃣ Execute**

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

> 🪟 **No Windows**, com o `.env` pronto, basta rodar `iniciar.bat`. O script procura `.venv` ou `venv`, verifica Python e dependências, confirma o `.env` e inicia a aplicação. Encerre com `Ctrl+C`.

> 🐧 **Linux ou macOS:** o comando Uvicorn é o mesmo, depois de criar/ativar um ambiente virtual e instalar o `requirements.txt`.

🎉 Ao iniciar, a aplicação testa a conexão com o Redis usando `PING`.

| 🔗 Recurso | Endereço |
|---|---|
| 🛍️ Loja (interface) | <http://127.0.0.1:8000> |
| 📖 Documentação interativa da API | <http://127.0.0.1:8000/docs> |
| 💓 Estado do serviço | <http://127.0.0.1:8000/health> |

> ⚠️ **O PowerShell bloqueou a ativação do ambiente?** Abra um terminal que permita executar o script de ativação ou use diretamente `.venv\Scripts\python.exe`.

> 🔥 Nunca compartilhe nem versione o arquivo `.env`, e não coloque credenciais reais no README ou em qualquer arquivo versionado.

---

## ⚙️ Variáveis de ambiente

Configure **uma** das duas opções de conexão.

**🅰️ Opção A: URL Redis**

```dotenv
REDIS_URL=redis://default:SENHA@HOST:PORTA
```

Substitua `SENHA`, `HOST` e `PORTA` pelos valores do serviço. Caracteres especiais na senha precisam estar codificados para URL.

**🅱️ Opção B: campos separados** (usada se `REDIS_URL` não estiver definida)

```dotenv
REDIS_HOST=seu-host-redis
REDIS_PORT=6379
REDIS_USERNAME=default
REDIS_PASSWORD=sua-senha
```

**🎛️ Opções da aplicação**

| Variável | Padrão | Descrição |
|---|---:|---|
| `REDIS_KEY_PREFIX` | `ecommerce` | Namespace das chaves Redis da aplicação |
| `AUTH_SESSION_TTL_SECONDS` | `604800` | Duração da sessão em segundos (sete dias) |
| `AUTH_COOKIE_SECURE` | `false` | Define se o cookie de sessão exige HTTPS |

> [!CAUTION]
> 🔓 A configuração atual conecta com `redis://` **sem TLS**, conforme o ambiente Redis Cloud Essentials Free usado no desenvolvimento. Use **apenas dados fictícios** nessa instância.
> Para produção são necessários: TLS no cliente Redis, HTTPS, `AUTH_COOKIE_SECURE=true` e revisão completa da configuração de segurança.

---

## 🗄️ Redis e persistência

O Redis é o **banco principal** da aplicação.

| Estrutura | 🎯 Uso |
|---|---|
| 🗂️ **Hashes** | Usuários, produtos, categorias e pedidos |
| 🧷 **Sets** | Índices e relações entre entidades |
| ⏳ **Strings com TTL** | Sessões |

- 🔐 Senhas são persistidas como hashes **Argon2id**; o token bruto da sessão **não** é armazenado como valor no Redis.
- 🛒 Carrinhos expiram após **sete dias** sem atualização.
- 📦 O estoque **não é reservado** enquanto o produto está na sacola: a disponibilidade é **revalidada atomicamente** no checkout.
- ↩️ O cancelamento de um pedido confirmado devolve o estoque **uma única vez**.

📚 Veja [docs/REDIS.md](docs/REDIS.md) para o inventário de chaves, campos e relacionamentos, e [docs/REDIS-COMANDOS.md](docs/REDIS-COMANDOS.md) para consultas no Redis CLI.

---

## 🧭 Como o checkout funciona

```mermaid
sequenceDiagram
    participant N as 🌐 Navegador
    participant R as 🛣️ Rota
    participant S as ⚙️ Service
    participant D as 🟥 Redis

    N->>R: Finalizar compra (sessão do cliente)
    R->>R: Valida sessão e perfil 🔐
    R->>S: checkout(sacola)
    S->>D: Revalida o estoque de forma atômica
    alt ❌ estoque insuficiente
        D-->>S: indisponível
        S-->>N: erro, pedido não registrado
    else ✅ estoque disponível
        D-->>S: confirmado
        S->>D: Registra o pedido e atualiza o estoque
        S-->>N: pedido confirmado 🎉
    end
```

> 💡 O pagamento **não** faz parte desse fluxo. O checkout é demonstrativo.

---

## 🧪 Testes

Com as dependências instaladas e o `.env` apontando para uma instância Redis **dedicada a testes**:

```powershell
python -m pytest -q
```

A suíte cobre: ✅ validação de schemas • ✅ conexão e persistência Redis • ✅ autenticação • ✅ autorização • ✅ perfis • ✅ produtos • ✅ categorias • ✅ carrinhos • ✅ pedidos.

> ⚠️ Os testes de integração criam registros temporários e os removem ao final. Ainda assim, execute-os **somente** em uma instância de teste, **nunca** contra dados de produção.
> Se o Redis não estiver configurado, os testes que dependem dele são ignorados conforme os fixtures.

---

## 📚 Documentação complementar

| 📄 Documento | 📝 Conteúdo |
|---|---|
| [Manual de execução e demonstração](docs/manual.md) | Como rodar e demonstrar o sistema |
| [Referência da API](docs/api.md) | Endpoints e contratos |
| [Modelagem Redis completa](docs/REDIS.md) | Chaves, campos e relacionamentos |
| [Cola de comandos Redis](docs/REDIS-COMANDOS.md) | Consultas no Redis CLI |
| [Resumo de modelagem Redis](docs/redis-model.md) | Visão resumida do modelo |
| [Histórico de progresso](PROGRESSO.md) | Evolução do projeto |

---


<div align="center">

### 👩‍💻 Autores

**Carolina Ribeiro**<br>
**Carlos Roberto**

⭐ Se curtiu o projeto, deixa uma estrela!

</div>
