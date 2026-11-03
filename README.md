# Linx — boas escolhas para o seu dia

Loja demonstrativa Linx, desenvolvida em Python com Redis Cloud como banco de
dados principal e frontend responsivo em HTML, CSS e JavaScript.

## Requisitos

- Python 3.11 ou superior.
- Uma instância Redis Cloud Essentials Free.
- Não é necessário instalar Redis localmente nem usar Docker ou WSL.

## Configuração no Windows

No PowerShell, a partir da raiz do projeto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edite `.env` e configure Redis Cloud em `REDIS_URL` ou use os campos
`REDIS_HOST`, `REDIS_PORT`, `REDIS_USERNAME` e `REDIS_PASSWORD`. O plano Free
utilizado não oferece TLS; a conexão é feita explicitamente com `ssl=False`.
Use apenas dados de teste nesse ambiente e não compartilhe nem versione `.env`.

## Executar

No Windows, execute `iniciar.bat` na raiz do projeto para ativar o ambiente
virtual existente, conferir as dependências e iniciar a aplicação. O arquivo
`.env` deve estar configurado com acesso ao Redis Cloud.

Como alternativa, inicie manualmente pelo terminal:

```powershell
python -m uvicorn backend.app.main:app --reload
```

A aplicação testa `PING` ao iniciar e não usa armazenamento alternativo. Sem
uma URL Redis Cloud válida, a inicialização falha explicitamente. A API fica
em `http://127.0.0.1:8000`; OpenAPI em `/docs` e saúde em `/health`.

O roteiro de demonstração e as limitações do projeto estão em
[docs/manual.md](docs/manual.md).

## Documentação do Redis

- [Modelagem, chaves e relacionamentos Redis](docs/REDIS.md)
- [Comandos de consulta para Redis CLI](docs/REDIS-COMANDOS.md)

Vendedores também podem se cadastrar pela interface, selecionando **Vendedor**
e preenchendo os dados da loja. O comando administrativo continua disponível
para provisionamento local (a senha é lida sem eco no terminal):

```powershell
python -m backend.app.scripts.create_seller --name "Nome" --email "vendedor@example.com"
```

O cadastro público aceita somente os perfis `client` e `seller`; o tipo de
conta não pode ser alterado após o cadastro. Login e sessão usam cookie
HttpOnly com sessão revogável no Redis. Para produção em HTTPS, configure
`AUTH_COOKIE_SECURE=true`; mantenha o Redis Cloud Free apenas para testes
fictícios, pois a instância utilizada não oferece TLS.

## Testes

```powershell
python -m pytest -q
```

Os testes de schema não exigem Redis. Os testes de integração de conexão,
persistência e CRUD usam a instância Redis Cloud configurada em `.env`; são
ignorados quando a configuração Redis não está definida. Eles criam e removem
chaves e produtos temporários no namespace configurado.

## Escopo atual

Implementados: configuração Redis Cloud, autenticação por sessão, perfis de
cliente e vendedor, CRUD de produtos com propriedade, carrinho e pedidos por
usuário autenticado, checkout simulado, histórico e cancelamento. A interface
exibe navegação e operações conforme o perfil.
