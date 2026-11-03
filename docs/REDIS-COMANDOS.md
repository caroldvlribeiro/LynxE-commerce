# Cola de comandos Redis — Linx

Abra `redis-cli` conectado à sua instância Redis Cloud. Os exemplos usam o
prefixo padrão `ecommerce`; troque-o pelo valor de `REDIS_KEY_PREFIX`. Troque
os valores entre `<...>` por IDs reais. Os comandos consultam dados; não use
`KEYS *` para varredura geral.

## Comandos básicos

| Comando | O que faz / quando usar | Exemplo real | Como interpretar |
|---|---|---|---|
| `PING` | Testa se a conexão está respondendo. | `PING` | `PONG` significa que o servidor respondeu. |
| `SCAN` | Percorre chaves em lotes sem a busca global bloqueante do `KEYS`. Repita com o cursor retornado até chegar a `0`. | `SCAN 0 MATCH ecommerce:* COUNT 100` | A resposta contém cursor e lote de nomes. Cursor diferente de `0` significa que a varredura não terminou. |
| `TYPE` | Descobre a estrutura armazenada numa chave antes de escolher o comando de leitura. | `TYPE ecommerce:user:<user_id>` | No projeto retorna `hash`, `set` ou `string` para as chaves correspondentes. |
| `EXISTS` | Confirma se uma chave existe. | `EXISTS ecommerce:cart:<client_id>` | `1` existe; `0` não existe. |
| `TTL` | Consulta segundos até expirar. | `TTL ecommerce:session:<sha256>` | Positivo: segundos restantes; `-1`: sem expiração; `-2`: chave ausente. |
| `HGETALL` | Lê todos os campos de um Hash pequeno. | `HGETALL ecommerce:product:<product_id>` | Pares campo/valor; `price_cents` está em centavos. O Hash de usuário contém `password_hash`: não exponha nem compartilhe sua saída. |
| `HGET` | Lê apenas um campo de Hash. | `HGET ecommerce:user:<user_id> role` | `client` ou `seller`; campo ausente retorna resposta vazia/nil. |
| `HSCAN` | Percorre os campos de um Hash em lotes, útil para registros grandes. Repita com o cursor retornado até chegar a `0`. | `HSCAN ecommerce:user:<user_id> 0 COUNT 20` | Cursor e pares de campos/valores; não imprime todos os campos de uma vez. |
| `GET` | Lê uma String. | `GET ecommerce:session:<sha256>` | Valor é o UUID do usuário. A chave usa digest do token; nunca compartilhe token de sessão. |
| `SMEMBERS` | Lista membros de um Set, adequado a índices pequenos/diagnóstico. | `SMEMBERS ecommerce:users` | Retorna UUIDs. Para conjuntos grandes, use `SSCAN`. |
| `SSCAN` | Percorre os membros de um Set em lotes sem carregá-lo todo numa resposta. Repita com o cursor retornado até `0`. | `SSCAN ecommerce:products 0 COUNT 100` | Cursor e parte dos IDs. `COUNT` é uma sugestão de tamanho do lote, não uma garantia exata. |
| `LRANGE` | Lê elementos de uma List. | — | Não há Lists na implementação Linx atual. |
| `ZRANGE` | Lê membros de um Sorted Set. | — | Não há Sorted Sets na implementação Linx atual. |
| `XLEN` / `XRANGE` | Consultam tamanho/entradas de um Stream. | — | Não há Streams na implementação Linx atual. |

Também são usadas as versões incrementais `SSCAN` para Sets. Não existe chave
de List, Sorted Set ou Stream no código atual.

## Usuários

IDs de todos os usuários:

```redis
SMEMBERS ecommerce:users
```

IDs só de cliente ou vendedor:

```redis
SMEMBERS ecommerce:users:role:client
SMEMBERS ecommerce:users:role:seller
```

Resolver e-mail para UUID (o código normaliza com `strip().casefold()`):

```redis
HGET ecommerce:users:by_email cliente@example.com
```

Consultar usuário depois de obter o UUID:

```redis
HGETALL ecommerce:user:<user_id>
HGET ecommerce:user:<user_id> role
HGET ecommerce:user:<user_id> created_at
HGET ecommerce:user:<user_id> store_name
HGET ecommerce:user:<user_id> store_description
HGET ecommerce:user:<user_id> business_phone
```

`role` identifica `client`/`seller`. Dados da loja ficam no mesmo Hash do
vendedor, não numa chave independente. `password_hash` também está nesse Hash:
é hash Argon2id, não senha em texto, mas deve continuar privado.

## Produtos e estoque

IDs de produtos e registro completo:

```redis
SMEMBERS ecommerce:products
HGETALL ecommerce:product:<product_id>
```

Vendedor proprietário e estoque:

```redis
HGET ecommerce:product:<product_id> seller_id
HGET ecommerce:product:<product_id> stock
HGET ecommerce:product:<product_id> price_cents
HGET ecommerce:product:<product_id> status
```

IDs dos produtos de um vendedor:

```redis
SMEMBERS ecommerce:seller:<seller_id>:products
```

`price_cents` usa centavos inteiros (ex.: `12200` = R$ 122,00). Produtos
legados podem não ter `seller_id`.

## Categorias

Listar IDs, procurar nome/token e abrir registro:

```redis
SMEMBERS ecommerce:categories
HGETALL ecommerce:categories:by_name
HGET ecommerce:categories:by_name Y2FzYQ
HGETALL ecommerce:category_record:<category_id>
```

`Y2FzYQ` corresponde ao token do nome `Casa` (normalizado para `casa`).
Produtos associados são indexados por Set:

```redis
SMEMBERS ecommerce:category:Y2FzYQ:products
```

O algoritmo normaliza o nome com casefold e colapso de espaços, codifica em
Base64 URL-safe e remove o padding `=`.

## Carrinho

O UUID do proprietário está no sufixo da chave. O Hash mapeia ID de produto
para quantidade:

```redis
HGETALL ecommerce:cart:<client_id>
HGET ecommerce:cart:<client_id> <product_id>
TTL ecommerce:cart:<client_id>
```

Não há nome/preço copiado para essa chave: o catálogo atual fornece os dados
do produto. TTL é de até 604800 segundos, renovado ao alterar o carrinho.
Checkout apaga o carrinho; remover o último item também exclui a chave.

## Pedidos

Listar IDs globais ou os IDs associados a um cliente:

```redis
SMEMBERS ecommerce:orders
SMEMBERS ecommerce:client:<client_id>:orders
```

Detalhes e snapshot JSON dos itens:

```redis
HGETALL ecommerce:order:<order_id>
HGET ecommerce:order:<order_id> client_id
HGET ecommerce:order:<order_id> status
HGET ecommerce:order:<order_id> items
HGET ecommerce:order:<order_id> total_cents
```

O `items` é um único campo JSON dentro do Hash, com `product_id`, `name`,
`category`, `quantity`, `unit_price_cents`, `subtotal_cents` e `image_url`.
Não há chave por item. `status` é `confirmed` ou `cancelled`; cancelamento
também registra `cancelled_at`.

Produtos envolvidos em pedidos confirmados:

```redis
SMEMBERS ecommerce:product:<product_id>:active_orders
```

Essa chave Set protege o produto de exclusão enquanto pedidos podem ser
cancelados. Ao cancelar, o estoque é devolvido e o ID do pedido sai do Set.

## Sessões

As sessões são Strings com TTL:

```redis
SCAN 0 MATCH ecommerce:session:* COUNT 100
TYPE ecommerce:session:<sha256>
TTL ecommerce:session:<sha256>
GET ecommerce:session:<sha256>
```

O nome da chave contém o SHA-256 do token de sessão; o valor contém o UUID do
usuário. O token bruto só fica no cookie `viva_session`. Não compartilhe
valores, cookies ou capturas dessas consultas.

## CLI de inspeção somente leitura

Na raiz do projeto, com `.env` configurado:

```powershell
python -m backend.app.scripts.inspect_redis
python -m backend.app.scripts.inspect_redis --limit 20
python -m backend.app.scripts.inspect_redis --pattern "ecommerce:product:*"
python -m backend.app.scripts.inspect_redis --key "ecommerce:products"
python -m backend.app.scripts.inspect_redis --key "ecommerce:user:<user_id>"
```

Sem `--key`, o script lista nomes/tipo/TTL por `SCAN` e informa
`possibly_truncated` se atingiu o limite. Com `--key`, mostra campos de Hash ou
membros de Set até `--limit`, com a indicação `truncated`; `password_hash` e
valores de sessão são redigidos. `--key` e `--pattern` são limitados ao
prefixo configurado. O limite padrão é 100 (máximo 1000). O script não
modifica dados.
