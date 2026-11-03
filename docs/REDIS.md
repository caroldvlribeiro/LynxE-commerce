# Redis Cloud: modelagem e referência dos dados Linx

Este documento descreve as chaves e os comandos encontrados na implementação
em `backend/app/repositories/`, `backend/app/db/redis.py`,
`backend/app/core/config.py` e `backend/app/services/auth_service.py`.
As chaves abaixo são padrões reais do código, não uma proposta de alteração
do banco.

## Conexão e namespace

A aplicação usa Redis Cloud como persistência principal, conecta com
`ssl=False` para a instância Essentials Free configurada no projeto e testa a
conexão com `PING` no startup. Configure `REDIS_URL` ou `REDIS_HOST`,
`REDIS_PORT`, `REDIS_USERNAME` e `REDIS_PASSWORD` no `.env`.

O prefixo é `REDIS_KEY_PREFIX`, com valor padrão `ecommerce`. Nos exemplos,
`{prefix}` significa esse valor, `{id}` é o UUID correspondente, e os trechos
entre `<...>` devem ser substituídos por valores reais. Não inclua as chaves
literais `{prefix}`, `<id>` ou `{id}` nos comandos.

O projeto cria apenas **Hashes**, **Sets** e **Strings**. Não foram encontrados
usos de Lists, Sorted Sets ou Streams.

## Inventário de chaves

| Chave ou padrão real | Tipo Redis | Conteúdo e finalidade | Relacionamentos, operações e expiração |
|---|---|---|---|
| `{prefix}:users` | Set | UUIDs de todos os usuários, cliente ou vendedor. Índice geral. | Criado ao cadastrar/provisionar usuário. A consulta é por `SMEMBERS`; sem exclusão de conta na API. Sem TTL. |
| `{prefix}:users:role:client` | Set | UUIDs de usuários cujo campo `role` é `client`. | Índice por papel; mantido no mesmo script Lua da criação. Sem TTL. |
| `{prefix}:users:role:seller` | Set | UUIDs de usuários cujo campo `role` é `seller`. | Índice por papel; mantido no mesmo script Lua da criação. Sem TTL. |
| `{prefix}:users:by_email` | Hash | Campo: e-mail normalizado; valor: UUID do usuário. E-mail é removido de espaços externos e submetido a `casefold()`. | Busca e login resolvem o UUID por `HGET`. Criação garante unicidade atomicamente; mudança de e-mail substitui o índice atomicamente. Sem TTL. |
| `{prefix}:user:{user_id}` | Hash | Dados de cliente/vendedor e, para vendedor, os dados da loja. | Associado aos Sets de usuários e ao índice de e-mail. Cadastro grava dados; perfil atualiza nome/e-mail, perfil do vendedor atualiza os campos comerciais, alteração de senha atualiza o hash. Sem TTL e sem rota de exclusão de conta. |
| `{prefix}:session:{sha256(token)}` | String | Valor: UUID do usuário autenticado. A chave contém o SHA-256 do token opaco; o token bruto só é enviado no cookie `viva_session`. | Criada no login com `SET ... EX ... NX`; consultada na autenticação de requisições e excluída no logout. TTL padrão de 604800 segundos (7 dias), configurável em `AUTH_SESSION_TTL_SECONDS`. |
| `{prefix}:products` | Set | UUIDs de todos os produtos, inclusive inativos. | Índice geral, criado/removido junto ao Hash do produto. Sem TTL. |
| `{prefix}:seller:{seller_id}:products` | Set | UUIDs dos produtos associados ao vendedor. | Índice por proprietário; atualizado na criação e exclusão do produto. Usado pelo catálogo do vendedor. Sem TTL. |
| `{prefix}:product:{product_id}` | Hash | Registro do produto, incluindo estoque e referência à categoria. | Referenciado nos índices geral, vendedor, categoria e, enquanto há pedido confirmado, índice `:active_orders`. Sem TTL. |
| `{prefix}:product:{product_id}:active_orders` | Set | UUIDs dos pedidos confirmados que incluem o produto e ainda podem ser cancelados. | Criado/atualizado no checkout; removido no cancelamento. O Set pode deixar de existir quando não tem membros. Protege o produto contra exclusão enquanto houver pedidos ativos. |
| `{prefix}:categories` | Set | UUIDs de todos os registros de categoria. | Índice geral de categorias; atualizado atomicamente com os Hashes e o índice por nome. Sem TTL. |
| `{prefix}:categories:by_name` | Hash | Campo: token do nome de categoria normalizado; valor: UUID da categoria. | Busca e validação de existência/duplicidade. Atualizado atomicamente ao criar, renomear ou excluir uma categoria. Sem TTL. |
| `{prefix}:category_record:{category_id}` | Hash | Registro da categoria: ID, nome, descrição, token normalizado, data e `seller_id`. | Produtos referenciam a categoria pelo nome e pelo Set derivado desse nome. Excluir categoria em uso é recusado. Sem TTL. |
| `{prefix}:category:{token}:products` | Set | UUIDs dos produtos atribuídos à categoria. | Índice de produtos por categoria; o token é o nome normalizado e codificado em Base64 URL-safe sem `=` final. Atualização de produto e renomeação de categoria mantêm o índice via Lua. Sets vazios podem desaparecer. Sem TTL. |
| `{prefix}:cart:{client_id}` | Hash | Campo: UUID de produto; valor: quantidade no carrinho. | O sufixo identifica o cliente autenticado. Cada mudança de quantidade reinicia TTL de 604800 segundos (7 dias); remover o último item ou concluir checkout exclui a chave. Não reserva estoque. |
| `{prefix}:orders` | Set | UUIDs de todos os pedidos. | Índice global atualizado atomicamente no checkout. Sem TTL. |
| `{prefix}:client:{client_id}:orders` | Set | UUIDs dos pedidos pertencentes ao cliente. | Índice usado para consultar apenas pedidos do próprio cliente. Atualizado atomicamente no checkout. Sem TTL. |
| `{prefix}:order:{order_id}` | Hash | Registro do pedido e snapshot JSON dos itens no campo `items`. | Referenciado pelos Sets global e do cliente. Checkout cria o registro; cancelamento altera status/data e restaura estoque. Sem TTL. |

### Campos dos registros principais

**Usuário — `{prefix}:user:{user_id}`**

| Campo | Significado |
|---|---|
| `id` | UUID do usuário. |
| `full_name` | Nome completo. |
| `email` | E-mail normalizado. |
| `password_hash` | Hash Argon2id; não é a senha em texto. Não compartilhe esse campo. |
| `role` | `client` ou `seller`; não há papel de administrador no schema público. |
| `status` | Estado da conta; contas novas são `active`. |
| `created_at` | Data/hora ISO 8601 em UTC. |
| `store_name` | Nome da loja de vendedor. Ausente ou string vazia equivale a `None`; não é outra chave. |
| `store_description` | Descrição da loja, armazenada no mesmo Hash. |
| `business_phone` | Telefone comercial opcional, armazenado no mesmo Hash. |

Os três últimos campos comerciais podem estar ausentes em contas antigas ou
vendedores criados anteriormente. Não há Hash separado para perfil de loja.

**Produto — `{prefix}:product:{product_id}`**

| Campo | Significado |
|---|---|
| `id` | UUID do produto. |
| `name`, `description` | Nome e descrição. |
| `category` | Nome canônico da categoria. |
| `category_index_key` | Chave Set atualmente associada ao produto. |
| `price_cents` | Preço inteiro em centavos; por exemplo, `12200` equivale a R$ 122,00. |
| `stock` | Estoque disponível como inteiro; reduzido no checkout e restaurado no cancelamento. |
| `image_url` | URL/caminho da imagem; pode estar vazio. |
| `status` | `active` ou `inactive`. |
| `created_at` | Data/hora ISO 8601 em UTC. |
| `seller_id` | UUID do vendedor proprietário; pode faltar em produtos legados. |

**Categoria — `{prefix}:category_record:{category_id}`**

Campos: `id`, `name`, `description`, `name_token`, `created_at` e `seller_id`.
O `name_token` resulta de `name.casefold()`, colapso de espaços consecutivos,
codificação Base64 URL-safe e remoção do padding `=`. Por exemplo, `Casa`
normaliza para `casa` e token `Y2FzYQ`.

**Pedido — `{prefix}:order:{order_id}`**

| Campo | Significado |
|---|---|
| `id` | UUID do pedido. |
| `client_id` | UUID do cliente autenticado que fez a compra. |
| `status` | `confirmed` ou `cancelled`. |
| `items` | Array JSON de snapshots; ver campos abaixo. |
| `total_cents` | Total em centavos. |
| `created_at` | Data/hora ISO 8601 em UTC. |
| `cancelled_at` | Data/hora ISO 8601 em UTC; só é acrescentado ao cancelar. |

Cada elemento de `items` contém `product_id`, `name`, `category`, `quantity`,
`unit_price_cents`, `subtotal_cents` e `image_url`. É uma fotografia dos dados
no checkout; alterações posteriores no produto não reescrevem o histórico.
Não há chave Redis separada para itens do pedido.

**Carrinho — `{prefix}:cart:{client_id}`**

Cada campo é o `product_id` e cada valor sua `quantity`. Nome, categoria,
preço e disponibilidade não são copiados para o carrinho: a aplicação consulta
os Hashes atuais dos produtos ao montar a resposta. Assim, não há snapshot de
preço antes do checkout.

## Organização e relacionamentos

```text
users (Set) ── user_id ──> user:{user_id} (Hash)
    ├── users:role:client (Set)
    ├── users:role:seller (Set)
    └── users:by_email (Hash: email normalizado -> user_id)
                                └── role=seller guarda os dados da loja

seller:{seller_id}:products (Set) ── product_id ──> product:{product_id} (Hash)
products (Set) ────────────────────┘                    ├── category_index_key
                                                        └── :active_orders (Set)
category_record:{category_id} (Hash)                    └── seller_id
categories (Set) ───────┘
categories:by_name (Hash: token -> category_id)
category:{token}:products (Set) ───── product_id ──> produto

user_id ──> cart:{client_id} (Hash: product_id -> quantity)
orders (Set) ───── order_id ──> order:{order_id} (Hash + items JSON)
client:{client_id}:orders (Set) ─┘
```

O Redis não implementa chaves estrangeiras. Os UUIDs nos Sets e campos de
referência ligam os registros. A identidade usada em carrinho e pedidos vem
da sessão autenticada, não de um ID arbitrário enviado pelo navegador.

### Consistência, atualização e exclusão

- Cadastro de usuário, unicidade de e-mail e índices geral/por papel são
  gravados num script Lua atômico. Mudança de e-mail remove o e-mail anterior,
  atualiza o Hash e associa o novo índice numa operação atômica.
- Senha é mantida como `password_hash` Argon2id. O login pode regravar esse
  campo se o algoritmo indicar necessidade de rehash.
- Criação de produto usa Lua para gravar o Hash e adicioná-lo aos índices
  geral, do vendedor e da categoria. Atualização mantém o Hash e move a
  associação de categoria quando necessário; os índices geral e do vendedor
  não mudam. Exclusão exige vendedor proprietário e nenhum pedido ativo, e
  remove Hash e associações dos Sets numa operação Lua.
- Criação/renomeação/exclusão de categoria também usa Lua. Renomear atualiza
  os produtos e o índice de categoria na mesma operação; categoria com
  produtos não pode ser excluída.
- Carrinho valida produto, status e estoque ao alterar quantidade. TTL é
  renovado a cada alteração; o carrinho não reserva estoque.
- Checkout valida todo o carrinho e estoque, cria o pedido com snapshot,
  reduz estoque, atualiza índices e apaga o carrinho atomicamente. Um produto
  associado a pedido confirmado fica protegido por `:active_orders`.
- Cancelamento só é aplicado uma vez: muda estado, registra `cancelled_at`,
  devolve estoque e retira o pedido dos Sets `:active_orders` via Lua.
- Sets não definem ordem. A API lista pedidos de cliente ordenando UUIDs
  lexicograficamente em ordem decrescente; como os UUIDs são aleatórios, essa
  ordem não representa necessariamente a data de criação.
- Não há operação de exclusão de usuário na API. Os dados principais e índices
  persistentes não expiram. Sessões e carrinhos são as chaves com TTL
  explícito na implementação.

`SMEMBERS` e outras consultas globais podem retornar conjuntos grandes. Use
`SSCAN`/`SCAN` para explorar volumes sem buscar tudo de uma vez.

## Consulta no Redis CLI

1. Abra Redis CLI usando os dados da seção **Connect** da sua instância Redis
   Cloud. Não coloque senha em arquivo, documentação ou histórico do terminal.
   O plano Free configurado neste projeto usa conexão sem TLS; ambientes
   diferentes podem exigir opções de TLS próprias.
2. Substitua `ecommerce` pelo valor configurado em `REDIS_KEY_PREFIX`.
3. Use os comandos de referência em [REDIS-COMANDOS.md](./REDIS-COMANDOS.md).

O script de inspeção opcional é somente de leitura:

```powershell
python -m backend.app.scripts.inspect_redis
python -m backend.app.scripts.inspect_redis --limit 20
python -m backend.app.scripts.inspect_redis --pattern "ecommerce:product:*"
python -m backend.app.scripts.inspect_redis --key "ecommerce:products"
python -m backend.app.scripts.inspect_redis --key "ecommerce:user:<user_id>"
```

O comando usa `SCAN`, exige que chave/padrão permaneça no namespace
configurado, mostra tipo e TTL ao listar, e limita a saída a 100 chaves por
padrão (máximo 1000). A propriedade `possibly_truncated` indica que a lista
atingiu o limite, portanto talvez haja mais resultados. Ao inspecionar um
registro, também limita campos/membros e informa `truncated`;
`password_hash` e valores de sessão são ocultados. Ele não cria, atualiza nem
remove chaves.

## Referência de implementação

- Conexão/configuração: `backend/app/core/config.py`,
  `backend/app/db/redis.py`.
- Usuários e sessões: `backend/app/repositories/user_repository.py`,
  `backend/app/services/auth_service.py`.
- Produtos: `backend/app/repositories/product_repository.py`.
- Categorias: `backend/app/repositories/category_repository.py`.
- Carrinhos: `backend/app/repositories/cart_repository.py`.
- Pedidos: `backend/app/repositories/order_repository.py`.
- CLI somente leitura: `backend/app/scripts/inspect_redis.py`.
