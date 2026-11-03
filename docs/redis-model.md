# Modelagem Redis

Esta nota resume a modelagem inicial. Para o inventário completo e atualizado
das chaves reais, campos, TTLs, relacionamentos e comandos de consulta, veja
[REDIS.md](./REDIS.md) e a [cola de comandos](./REDIS-COMANDOS.md).

## Persistência do catálogo

Os preços são armazenados em centavos inteiros para evitar imprecisão de ponto
flutuante. Cada produto fica em um Hash:

O plano Redis Cloud Essentials Free usado no projeto não oferece TLS. A conexão
é configurada centralmente com `ssl=False`; não armazenar dados sensíveis ou
credenciais de clientes nessa instância.

| Chave | Tipo | Conteúdo |
|---|---|---|
| `{prefix}:product:{id}` | Hash | `id`, `name`, `description`, `category`, `category_index_key`, `price_cents`, `stock`, `image_url`, `status`, `created_at`, `seller_id` (ausente em registros legados) |
| `{prefix}:products` | Set | IDs de todos os produtos |
| `{prefix}:seller:{seller_id}:products` | Set | IDs de produtos de cada vendedor |
| `{prefix}:category:{token}:products` | Set | IDs de produtos da categoria; token de nome normalizado e codificado em Base64 URL-safe |
| `{prefix}:category_record:{id}` | Hash | ID, nome, descrição, token do nome, vendedor responsável e data de cadastro |
| `{prefix}:categories` | Set | IDs das categorias |
| `{prefix}:categories:by_name` | Hash | Token normalizado do nome para ID da categoria |
| `{prefix}:user:{id}` | Hash | ID, nome, e-mail, hash Argon2id da senha, perfil, status, data de cadastro e, para vendedores, nome/descrição da loja e telefone comercial opcional |
| `{prefix}:users:by_email` | Hash | E-mail normalizado para ID do usuário |
| `{prefix}:users` e `{prefix}:users:role:{role}` | Sets | Índices de usuários e de cada perfil (`client`, `seller`) |
| `{prefix}:session:{sha256(token)}` | String com TTL | ID do usuário da sessão; o token bruto só fica no cookie HttpOnly |

O prefixo padrão é `ecommerce` e pode ser alterado por `REDIS_KEY_PREFIX`.
O nome de categoria é único sem distinção entre maiúsculas/minúsculas.
Produtos novos ou atualizados devem referenciar uma categoria cadastrada.
Criar/atualizar/excluir produtos e categorias mantém Hashes e índices por
scripts Lua atômicos. Renomear categoria atualiza os produtos associados e seu
índice na mesma operação; excluir categoria em uso retorna conflito.

Criar, atualizar e excluir produtos usam scripts Lua para alterar o Hash e
seus índices na mesma operação atômica, incluindo o índice do vendedor.
Propriedade é verificada no script de exclusão/atualização, não apenas no
serviço. Produtos legados sem `seller_id` permanecem no catálogo quando ativos
e não são editáveis por vendedor. As consultas por categoria usam o Set correspondente. A pesquisa por nome percorre os IDs indexados e lê os
Hashes em pipeline; é simples para o porte do projeto, mas cresce linearmente
com o catálogo. A paginação limita a resposta, não o custo de uma pesquisa
textual.

Usuários têm e-mail único garantido em script Lua. As senhas são armazenadas
somente como hash Argon2id. Sessões opacas possuem TTL e são revogadas no
logout; o Redis armazena o digest SHA-256 do token, não o segredo do cookie.
Carrinhos e pedidos usam o UUID autenticado como proprietário e as rotas não
aceitam identidade de usuário enviada pelo cliente.

## Pedidos

- `order:{id}` (Hash): UUID do cliente, status, total em centavos, data e itens
  serializados como snapshot de nome, categoria, preço e quantidade.
- `orders` e `client:{id}:orders` (Sets): índices para listagem.
- `product:{id}:active_orders` (Set): pedidos confirmados que ainda podem ser
  cancelados. Impede exclusão do produto até que o pedido seja cancelado.
- Checkout e cancelamento executam scripts Lua: verificam todos os dados antes
  de alterar estoque e só então gravam pedido/índices ou devolvem o estoque.
  Assim, um erro em um item não deixa baixa parcial.

## Limitações e consistência

Carrinhos usam `cart:{client_id}` como Hash de produto para quantidade, em que
`client_id` vem da sessão autenticada, com expiração de sete dias após cada alteração. Um script Lua
valida que o produto existe, está ativo e tem estoque para a operação antes
de alterar o carrinho. O carrinho não reserva estoque; compras simultâneas
serão revalidadas atomicamente no checkout. O total e os subtotais são
calculados usando os preços atuais do catálogo.

O checkout confirma e baixa estoque atomicamente, armazenando snapshot para
preservar histórico. O cancelamento restaura estoque exatamente uma vez.
Produtos de pedidos confirmados ficam protegidos contra exclusão para que
cancelamentos futuros possam devolver estoque com consistência.

Redis não fornece chaves estrangeiras nem transações relacionais com rollback.
Os scripts Lua garantem atomicidade para as operações críticas, mas toda
alteração de produto deverá manter os índices. O catálogo e as pesquisas
crescem em memória; o limite de 30 MB exige evitar campos desnecessários,
expirar carrinhos e monitorar consumo. Não se usa `KEYS`; os índices explícitos
evitam varredura global de chaves.
