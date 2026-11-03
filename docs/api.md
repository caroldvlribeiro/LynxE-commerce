# API REST — Linx

Base URL local: `http://127.0.0.1:8000`

O nome Linx identifica a loja e a documentação OpenAPI. O cookie de sessão
mantém o identificador interno legado `viva_session` para preservar sessões e
compatibilidade com os clientes existentes.

## Saúde e Redis

`GET /health` testa a conexão com Redis.

Resposta `200`:

```json
{"status": "ok", "redis": "connected"}
```

## Autenticação e perfis

As sessões são armazenadas no Redis e autenticadas por um cookie opaco
`HttpOnly`, `SameSite=Strict`, chamado `viva_session`. O token bruto não fica
no frontend nem é armazenado no Redis; o servidor guarda seu digest SHA-256.

- `POST /api/v1/auth/register` — cria uma conta cliente ou vendedor. Recebe
  `full_name`, `email`, `password` (mínimo 12 caracteres, com maiúscula,
  minúscula e número) e `role` (`client` ou `seller`; padrão `client`).
  Vendedores também informam `store_name` e `store_description`; `business_phone`
  é opcional. Campos comerciais são rejeitados para clientes e e-mail duplicado
  retorna `409`.
- `POST /api/v1/auth/login` — recebe e-mail e senha, configura o cookie de
  sessão e retorna os dados públicos do usuário.
- `POST /api/v1/auth/logout` — invalida a sessão no Redis e remove o cookie.
- `GET /api/v1/auth/me` — retorna o usuário autenticado; sem sessão válida
  responde `401`.
- `PATCH /api/v1/auth/profile` — atualiza `full_name` e/ou `email` da própria
  conta. O perfil não faz parte dos campos aceitos.
- `PATCH /api/v1/auth/seller-profile` — vendedor autenticado atualiza
  `store_name`, `store_description` e/ou `business_phone`.
- `POST /api/v1/auth/password` — altera a senha após validar
  `current_password`; a nova senha deve cumprir os mesmos requisitos de força.

Vendedores também podem se cadastrar publicamente. Para provisionamento local
por um administrador com acesso ao ambiente Redis Cloud:

```powershell
python -m backend.app.scripts.create_seller --name "Nome" --email "vendedor@example.com"
```

A senha é solicitada sem eco no terminal. O cadastro permite somente os perfis
`client` e `seller`; endpoints de perfil não aceitam alteração de role. As
rotas de alteração de estado verificam a origem da requisição; mantenha HTTPS e
habilite `AUTH_COOKIE_SECURE=true` quando publicar a aplicação. O Redis
Essentials Free usado nesta demonstração não oferece TLS e deve conter apenas
dados fictícios.

## Produtos

Todos os endpoints de catálogo usam o prefixo `/api/v1`.

### Criar (vendedor autenticado)

`POST /api/v1/products` — resposta `201`.

```json
{
  "name": "Caneca",
  "description": "Caneca de cerâmica",
  "category": "Casa",
  "price": "29.90",
  "stock": 12,
  "image_url": "/images/caneca.jpg",
  "status": "active"
}
```

O campo `image_url` pode ser omitido. `price` deve ser positivo e ter no
máximo duas casas decimais; `stock` é inteiro não negativo. O ID UUID e a
data de cadastro são gerados pelo backend. Nas respostas, `price` é uma
string decimal com duas casas (por exemplo, `"29.90"`) para preservar exatidão.
O `seller_id` é sempre derivado da sessão, nunca aceito do corpo.

### Listar, pesquisar e filtrar

`GET /api/v1/products?search=caneca&category=Casa&limit=20&offset=0` é o
catálogo público e retorna somente produtos ativos.

`GET /api/v1/products/mine` lista os produtos do vendedor autenticado,
incluindo os inativos. Requer perfil vendedor.

```json
{
  "items": [],
  "total": 0,
  "limit": 20,
  "offset": 0
}
```

`search` procura parte do nome sem distinguir maiúsculas/minúsculas.
`category` filtra pela categoria (sem distinguir maiúsculas/minúsculas).
`limit` aceita de 1 a 100; `offset` deve ser não negativo.

### Consultar por ID

`GET /api/v1/products/{id}` é público para produtos ativos. Produtos inativos
só podem ser consultados pelo vendedor proprietário; produto inexistente ou
sem permissão responde `404`.

### Atualizar

`PUT /api/v1/products/{id}` substitui os campos editáveis e responde `200`.
Requer vendedor proprietário; produto inexistente/de outro vendedor retorna
`404`. O corpo segue o formato da criação.

### Excluir

`DELETE /api/v1/products/{id}` requer vendedor proprietário e responde `204`;
produto inexistente/de outro vendedor retorna `404`. Produto usado por pedido
confirmado não pode ser removido até o cancelamento do pedido (`409`).
Produtos antigos sem `seller_id` continuam visíveis no catálogo quando ativos,
mas não podem ser alterados por vendedores.

Entradas inválidas retornam `422`. Falhas de comunicação com Redis retornam
`503`. A especificação interativa fica em `/docs` quando a API estiver em
execução.

## Categorias

### Criar

`POST /api/v1/categories` requer vendedor autenticado; a categoria fica
associada ao vendedor e responde `201`.

```json
{
  "name": "Casa",
  "description": "Utensílios e decoração"
}
```

Nomes são únicos sem distinção entre maiúsculas/minúsculas. Duplicatas
respondem `409 Conflict`.

### Listar e consultar

- `GET /api/v1/categories` — retorna `{ "items": [...], "total": 1 }`.
- `GET /api/v1/categories/{id}` — responde `200` ou `404`.

### Atualizar

`PUT /api/v1/categories/{id}` requer o vendedor proprietário. Renomear atualiza
atomicamente o nome e os índices dos produtos associados; não é permitido
renomear categorias legadas ou que contenham produtos de outro vendedor.
Nome duplicado ou categoria em uso de modo incompatível responde `409`;
ID inexistente/de outro vendedor responde `404`.

### Excluir

`DELETE /api/v1/categories/{id}` requer vendedor proprietário e responde `204`
quando a categoria está vazia. Categorias associadas a produtos respondem
`409`; categoria de outro vendedor retorna `404`.

Produtos só podem ser criados ou atualizados com uma categoria cadastrada;
categoria desconhecida responde `422`.

## Carrinho

Todas as rotas exigem perfil cliente. O ID do cliente é derivado da sessão; a
API não aceita UUID de cliente fornecido pelo navegador. Cada atualização
renova a expiração do carrinho para sete dias. O estoque não é reservado no
carrinho e é revalidado atomicamente no checkout.

- `GET /api/v1/carts` — consulta itens, quantidades e total.
- `POST /api/v1/carts/items` — adiciona quantidade ao item.
- `PUT /api/v1/carts/items/{product_id}` — substitui quantidade;
  corpo: `{ "quantity": 2 }`.
- `DELETE /api/v1/carts/items/{product_id}` — remove o item
  (resposta `204`).

Exemplo de adição:

```json
{
  "product_id": "UUID-do-produto",
  "quantity": 2
}
```

Consulta retorna `client_id` associado à sessão, lista de itens com preço
unitário e subtotal, `total_items` e total calculado pela API. Preços no
carrinho refletem o preço atual do catálogo; o checkout grava snapshots no
pedido.
Produto inativo ou quantidade acima do estoque retorna `409`; produto
inexistente retorna `404`. Se um produto for removido ou seu estoque/status
deixar de atender a quantidade no carrinho, a consulta marca o item como
indisponível; ele não entra no total e pode ser removido pelo endpoint DELETE.

## Pedidos

Não há pagamento real. O checkout cria um pedido confirmado e baixa o estoque
atomicamente; preços, nomes e demais dados exibidos no pedido são snapshots do
momento da compra. Todas as rotas exigem perfil cliente e usam o ID derivado
da sessão.

- `POST /api/v1/orders` — finaliza o carrinho; responde `201`.
  Carrinho vazio ou item indisponível responde `409`.
- `GET /api/v1/orders?limit=20&offset=0` — lista somente pedidos do usuário.
- `GET /api/v1/orders/{order_id}` — consulta pedido próprio; pedido de outra
  pessoa responde `404`.
- `PATCH /api/v1/orders/{order_id}/status` — atualiza o status do pedido
  próprio.

Corpo de atualização de status:

```json
{"status": "cancelled"}
```

Uma única transição de `confirmed` para `cancelled` devolve ao estoque as
quantidades registradas no snapshot. Repetir cancelamento ou reativar pedido
cancelado responde `409`. Produtos vinculados a pedidos confirmados não podem
ser excluídos; após cancelamento, podem ser removidos sem perder o histórico.
Pedidos antigos continuam acessíveis apenas pelo proprietário autenticado, de
acordo com o índice Redis `client:{id}:orders`.
