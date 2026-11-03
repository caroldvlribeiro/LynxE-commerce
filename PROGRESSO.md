# Progresso do projeto

## Estado atual — cadastro, perfil e autorização concluídos

### Etapas concluídas

Além da base de autenticação e autorização, o cadastro público agora permite
escolher entre cliente e vendedor, com perfis próprios, edição de dados e
persistência Redis. Interface, permissões, testes e documentação estão
integrados ao projeto existente.

### Implementado

- Cadastro público de clientes e vendedores, login/logout, identificação do
  usuário e sessão opaca revogável no Redis. Cookie `HttpOnly` e `SameSite=Strict`;
  Swagger/OpenAPI declara o cookie como esquema de segurança.
- Senhas protegidas com Argon2id. O Redis armazena somente o hash da senha e
  o digest SHA-256 do token de sessão; não há token no `localStorage`.
- Cadastro de vendedor exige nome e descrição da loja; telefone é opcional.
  Informações comerciais são guardadas no Hash do usuário sem substituir
  chaves de produtos nem alterar ownership.
- Perfis autenticados podem editar seus próprios dados; vendedor pode editar
  dados comerciais. Alteração de senha exige a senha atual. O tipo da conta
  não pode ser alterado após o cadastro.
- Guardas de role em rotas backend, validação de origem nas mutações e
  verificação atômica de propriedade em operações Redis de produto/categoria.
- Produtos novos e categorias vinculados ao vendedor. Produtos legados sem
  proprietário continuam visíveis quando ativos e não podem ser alterados.
- Carrinhos e pedidos obtêm identidade da sessão; APIs não aceitam ID de
  cliente no caminho/query. Cliente só consulta os próprios pedidos; checkout
  revalida estoque atomicamente e permanece simulado.
- Frontend com seleção de perfil no cadastro, campos comerciais condicionais,
  confirmação de senha, painel pessoal por papel e navegação contextual.
  Gerenciamento de produtos/categorias e experiência de compra preservados.
- Documentação da API, modelagem Redis, execução e demonstração atualizadas.

### Arquivos criados/modificados

- Backend de auth: `backend/app/core/{auth,config}.py`,
  `backend/app/schemas/user.py`,
  `backend/app/repositories/user_repository.py`,
  `backend/app/services/auth_service.py`,
  `backend/app/api/routes/auth.py`,
  `backend/app/scripts/create_seller.py`, `backend/app/main.py`,
  `requirements.txt`.
- Permissões/ownership: schemas, repositórios, serviços e rotas de produtos,
  categorias, carrinho e pedidos em `backend/app/`.
- Testes: `backend/tests/auth_helpers.py`,
  `backend/tests/test_auth_api.py`,
  `backend/tests/test_authorization_api.py` e testes existentes de produtos,
  categorias, carrinho e pedidos adaptados para autenticação.
- Interface: `frontend/{index.html,styles.css,app.js}`.
- Documentação/configuração: `README.md`, `PROGRESSO.md`,
  `.env.example` e `docs/{api.md,redis-model.md,manual.md}`.

### Estruturas Redis adicionadas

- `{prefix}:user:{id}` Hash com dados do usuário e hash Argon2id.
- `{prefix}:users:by_email` Hash para e-mail normalizado → ID.
- `{prefix}:users` e `{prefix}:users:role:{client|seller}` Sets.
- `{prefix}:session:{sha256(token)}` String com TTL e ID do usuário.
- `seller_id` no Hash de produto/categoria e
  `{prefix}:seller:{seller_id}:products` Set.
- Carrinhos continuam em `{prefix}:cart:{client_id}`; pedidos em
  `{prefix}:order:{id}` e `{prefix}:client:{client_id}:orders`. O ID é agora
  derivado da sessão autenticada.

### Validação e problemas conhecidos

- `python -m pytest -q`: **19 passed** contra Redis Cloud.
- `python -m compileall -q backend`: passou.
- `node --check frontend\app.js`: passou.
- Smoke test no navegador: cadastro, edição de perfil e loja, troca de senha,
  logout/login de vendedor; cadastro/login e perfil de cliente.
- Validação mobile a 390 px sem overflow horizontal. Redis Cloud respondeu
  `connected`; OpenAPI lista todas as rotas de perfil.
- Redis Cloud Essentials Free não oferece TLS: usar somente dados fictícios.
  Produção exige Redis com TLS, HTTPS e `AUTH_COOKIE_SECURE=true`.
- Não havia painel de vendas pré-existente para reaproveitar; pagamentos reais
  continuam fora do escopo. Produtos legados permanecem sem owner e read-only
  para vendedores, conforme decisão aprovada.

### Estado no checkpoint anterior à etapa de cadastro/perfil

Na pausa anterior, o servidor Uvicorn local foi encerrado. Para retomar a
aplicação, execute `python -m uvicorn backend.app.main:app --host 127.0.0.1
--port 8000`. Vendedores podem se cadastrar pela interface ou ser provisionados
com `python -m backend.app.scripts.create_seller`. Não usar dados pessoais ou
senhas reais no Redis Cloud atual.

## 2026-11-02 — Operação pausada

- Servidor local encerrado; nenhum processo de desenvolvimento deve permanecer
  ativo.
- Implementação, testes e documentação estão registrados acima.
- Próxima ação, caso solicitada: retomar a demonstração ou manutenção a partir
  do estado concluído, sem repetir alterações já validadas.

## 2026-11-03 — Continuidade da manutenção

- Retomada a partir do estado concluído, sem repetir alterações de
  implementação.
- Suíte completa revalidada no ambiente virtual do projeto:
  `python -m pytest -q` — **18 testes passaram**.
- Backend e frontend executados em `http://127.0.0.1:8000`; `/health`
  confirmou `Redis: connected`.

## 2026-11-03 — Identidade visual Linx

- Marca aplicada ao cabeçalho, rodapé, catálogo, diálogos de login/cadastro,
  mensagens de sessão, título da página, favicon e metadados OpenAPI.
- Tema centralizado em variáveis CSS: amarelo `#F2C230`, grafite `#242521`,
  fundo `#F8F7F2`, superfície `#FFFFFF`, texto secundário `#696B65`,
  borda `#E5E3DB`; estados usam verde `#256443`, aviso `#805600` e erro
  `#A53D32`, com fundos suaves próprios.
- Interface reorganizada e responsiva, com foco visível, estados de botão,
  formulários consistentes e cartões de produto atualizados.
- URLs de CSS e JavaScript versionadas para evitar que o navegador mantenha o
  tema anterior em cache.
- Validação: `node --check frontend\app.js`, `python -m compileall -q backend`
  e `python -m pytest -q` passaram; **18 testes aprovados**.
- No navegador foram conferidos catálogo real, busca, filtro, detalhes,
  abertura dos diálogos de login/cadastro e layouts desktop/mobile (390 px),
  sem overflow horizontal. A suíte de integração cobre autenticação e
  autorização. O `401` em `/auth/me` para visitante sem sessão é esperado e
  tratado como estado deslogado pelo frontend.
- Arquivos atualizados: `frontend/index.html`, `frontend/styles.css`,
  `frontend/app.js`, `backend/app/main.py`, `README.md`, `docs/api.md`,
  `docs/manual.md` e este registro; criado `frontend/favicon.svg`.
- O cookie de sessão preserva o identificador interno legado
  `viva_session` para não invalidar sessões existentes; isso não aparece na
  identidade visual da loja.
- Servidor foi mantido ativo para demonstração durante aquela etapa; foi
  reiniciado para a etapa de cadastro/perfil e encerrado após a validação final.

## 2026-11-03 — Cadastro e perfil (concluído)

- Implementado cadastro público com perfil limitado ao enum existente
  `client`/`seller`; vendedores devem enviar nome e descrição da loja, com
  telefone opcional e validado. Hash de senha Argon2id e unicidade do e-mail
  preservados.
- Redis agora grava os dados comerciais no mesmo Hash de usuário. Os campos
  são opcionais ao ler registros antigos e vendedores provisionados antes da
  alteração; nenhuma chave ou relação de produto foi substituída.
- Adicionadas operações autenticadas para editar dados pessoais, editar
  dados comerciais (somente vendedor) e alterar senha após verificar a senha
  atual. Atualização de e-mail e índice de e-mail é atômica no Redis.
- Rotas incluídas: `PATCH /api/v1/auth/profile`,
  `PATCH /api/v1/auth/seller-profile` e `POST /api/v1/auth/password`.
- Interface com cartões selecionáveis, campos de vendedor condicionais,
  confirmação de senha e painel de perfil para cada papel. As áreas de pedidos,
  catálogo, gerenciamento, carrinho e logout preservam as guardas existentes.
- Os arquivos de backend e teste adicionados/alterados incluem
  `backend/app/schemas/user.py`,
  `backend/app/repositories/user_repository.py`,
  `backend/app/services/auth_service.py`,
  `backend/app/api/routes/auth.py`,
  `backend/tests/test_auth_api.py` e
  `backend/tests/test_profile_api.py`.
- Validação final: `python -m pytest -q` (**19 passaram**), `python -m
  compileall -q backend` e `node --check frontend\app.js` passaram. O teste de
  integração cobre cadastro dos papéis, validações, permissões, pedidos,
  senha, persistência e preservação do produto após editar a loja.
- No navegador, Redis respondeu `connected`; cadastro e login reais de cliente
  e vendedor, edição pessoal/comercial, troca de senha, persistência após
  logout/login, painel por perfil e tela mobile a 390 px foram validados.
- A validação encontrou o seletor de cadastro mantendo campos/CTA de vendedor
  depois de resetar o formulário. O frontend agora reaplica o estado do papel
  após o reset; cadastro subsequente como cliente foi testado no navegador.
- Contas temporárias criadas no navegador foram removidas do Redis após os
  testes. O `401` inicial em `/auth/me` sem sessão é o comportamento esperado
  da API e é tratado como visitante pelo frontend.
- Documentação atualizada em `README.md`, `docs/api.md`, `docs/manual.md` e
  `docs/redis-model.md`. Servidor encerrado após a validação.

## 2026-11-03 — Documentação e inspeção do Redis

- Mapeadas as chaves Redis diretamente nos repositórios e scripts Lua
  embutidos: usuários/sessões, produtos/estoque, vendedores, categorias,
  carrinhos, pedidos e índices relacionados. A implementação usa Hash, Set e
  String; não usa List, Sorted Set ou Stream.
- Criado `docs/REDIS.md` com padrões e campos exatos, relacionamentos, índices,
  consistência atômica, TTLs e limites de compatibilidade de registros legados.
- Criado `docs/REDIS-COMANDOS.md` com comandos Redis CLI, exemplos por recurso,
  interpretação dos resultados e alternativas incrementais `SCAN`/`SSCAN`.
- Criado `backend/app/scripts/inspect_redis.py`, CLI somente leitura com
  varredura limitada ao namespace configurado; redige `password_hash` e valores
  de sessão. O README aponta para as duas novas referências.
- `docs/redis-model.md` agora encaminha para a documentação detalhada.
- Validação: Pylance sem diagnósticos e sintaxe Python válida; CLI conectou ao
  Redis Cloud, listou chaves com `SCAN`, inspecionou um Set e recusou chave fora
  do namespace. `python -m pytest -q` — **19 passaram**; `compileall` passou.
- O script foi exercitado sem gravar ou remover dados Redis.

## Histórico — estado anterior à implementação de autenticação

### Estado atual

O conteúdo abaixo registra o estado do projeto antes da implementação de
autenticação e autorização. A seção acima é a referência vigente.

### Implementado

- Estrutura modular inicial do backend FastAPI.
- Configuração por `.env`, aceitando URL `redis://` ou campos separados do
  Redis Cloud, com prefixo de chaves configurável.
- Conexão Redis com teste `PING` no startup e fechamento no shutdown.
- Fábrica central Redis configurada para o plano Essentials Free sem TLS;
  seleciona explicitamente a conexão não criptografada (`ssl=False`) sem
  passar parâmetro incompatível ao redis-py.
- Endpoint `/health`.
- CRUD de produtos via API REST, validação Pydantic, pesquisa por nome,
  filtro por categoria e paginação.
- CRUD de categorias com nomes únicos, validação referencial de produtos,
  bloqueio de exclusão quando associada e renomeação atômica dos índices.
- Carrinho por UUID com consulta, adição, atualização e remoção de itens;
  script Lua valida status/estoque e renova TTL de sete dias.
- Subtotais e total calculados no backend com aritmética decimal exata.
- Checkout simulado, consulta/listagem de pedidos, snapshots de compra e
  cancelamento com devolução atômica do estoque.
- Produtos associados a pedidos confirmados são protegidos contra exclusão;
  após cancelamento, podem ser removidos sem perder o snapshot do pedido.
- Loja responsiva integrada à API: catálogo, busca/filtro, detalhes, sacola,
  checkout, histórico de pedidos e cancelamento.
- Painel acadêmico de CRUD de produtos e categorias, com feedback de sucesso
  e erro consumido da API.
- Scripts Lua para manter Hash e índices de produto/categoria atomicamente.
- Documentação da API, modelagem Redis, configuração, execução e roteiro de
  demonstração.
- Testes unitários de schema e testes de integração CRUD/persistência que
  exigem Redis Cloud real.
- Teste dedicado de `PING` e leitura do valor temporário por uma segunda
  conexão Redis.
- Testes de integração do CRUD de categorias, duplicidade, renomeação,
  integridade referencial e associação de produto.
- Testes de integração do carrinho: soma de quantidades, estoque excedido,
  produto inativo/inexistente, totais, TTL e remoção de itens.
- Testes de integração de checkout, snapshot de preço/nome, baixa e devolução
  de estoque, cancelamento idempotente, consulta por cliente e histórico.
- Smoke test no navegador: cadastro de categoria/produto, catálogo, adição ao
  carrinho, checkout e cancelamento; dados de demonstração removidos.

### Arquivos criados

- `backend/app/main.py`; `backend/app/core/config.py`;
  `backend/app/db/redis.py`.
- Rotas: `backend/app/api/routes/{health,products,categories,carts,orders}.py`.
- Schemas: `backend/app/schemas/{product,category,cart,order}.py`.
- Serviços: `backend/app/services/{product,category,cart,order}_service.py`.
- Repositórios: `backend/app/repositories/{product,category,cart,order}_repository.py`.
- Testes: `backend/tests/test_{product_schema,products_api,redis_connection,categories_api,carts_api,orders_api}.py`.
- Interface: `frontend/{index.html,styles.css,app.js}`.
- Documentação: `docs/{api.md,redis-model.md,manual.md}`.
- Raiz: `requirements.txt`, `.env.example`, `.gitignore`, `README.md`,
  `PROGRESSO.md`; arquivos `__init__.py` para os pacotes Python.

Nenhum arquivo pré-existente de código foi substituído. O `.env` configurado
localmente pelo usuário não foi alterado nem teve seus segredos exibidos.

### Banco Redis Cloud

- Conexão real testada no plano Essentials Free sem TLS; a conexão é
  centralizada e usa explicitamente `ssl=False`.
- Prefixo configurável por `REDIS_KEY_PREFIX`. Chaves principais:
  `product:{id}`, `products`, `category_record:{id}`, `categories`,
  `categories:by_name`, `category:{token}:products`, `cart:{client_id}`,
  `order:{id}`, `orders`, `client:{id}:orders` e
  `product:{id}:active_orders`.
- Hashes armazenam registros/snapshots; Sets mantêm índices; scripts Lua
  protegem checkout, cancelamento e atualizações relacionais.
- Chaves de integração e registros temporários criados nos testes foram
  removidos. Não armazenar dados pessoais/sensíveis nem credenciais de clientes
  nessa instância sem TLS.

### Decisões

- FastAPI e redis-py assíncrono.
- A instância Essentials Free não oferece TLS; usar somente dados de teste,
  sem dados sensíveis nem credenciais de clientes.
- Preços armazenados em centavos inteiros.
- Categorias possuem UUID, nome normalizado único e descrição; produtos guardam
  o nome canônico e o índice reverso é atualizado atomicamente.
- Carrinhos são identificados por UUID sem autenticação; não guardar dados
  pessoais. O estoque não é reservado até checkout e os preços do carrinho
  acompanham o preço atual do catálogo.
- Checkout registra preço/nome do momento da compra e baixa estoque num script
  Lua. Cancelamento só é permitido uma vez e devolve estoque numa operação
  atômica. UUID do cliente não substitui autenticação.
- Sem Redis local, Docker, WSL ou banco de substituição.

### Validação e pendências

- Dependências instaladas em `.venv`.
- `pytest -q`: 15 passaram contra Redis Cloud, sem testes ignorados.
- A suíte cobre conexão/persistência, CRUD de produtos/categorias, integridade
  referencial, carrinho, checkout, snapshots, cancelamento e estoque.
- Teste real confirmou `PING`, gravação temporária, leitura após reconexão,
  remoção e confirmação de que a chave não existe mais.
- `compileall` passou; OpenAPI publica rotas de saúde, produtos, categorias,
  carrinho e pedidos.
- `node --check frontend/app.js` passou; página local respondeu `200` e foi
  exercitada no navegador.
- Fluxo de navegador confirmado: catálogo, sacola, checkout e cancelamento;
  gerenciamento de categoria e limpeza dos dados temporários verificados.
- Nenhum valor de credencial foi exibido ou alterado.
- Sem pagamento real, autenticação ou interface mobile testada em dispositivo;
  o ambiente não TLS é apenas para demonstração com dados de teste.
- Vídeo/apresentação final ainda precisa ser preparado pela dupla.

### Próxima ação

Usar [docs/manual.md](docs/manual.md) como roteiro e preparar a apresentação
acadêmica. Para retomar manutenção: ler este arquivo e o README, confirmar que
o `.env` local aponta para o Redis Cloud de teste sem compartilhar credenciais,
executar `python -m pytest -q` e só então implementar novas funcionalidades.

## 2026-11-03 — Melhorias de UX, acessibilidade e interação

- Cabeçalho sticky com navegação anunciando a página atual; troca entre as
  seções guarda e restaura a posição de rolagem durante a sessão.
- Formulários com validação inline, mensagens por campo, estados inválido/válido,
  indicação de obrigatoriedade, feedback de envio e prevenção de cliques
  repetidos. Campos preservam o que foi digitado em caso de erro.
- Botões acessíveis de mostrar/ocultar em todos os campos de senha; validação
  de confirmação e dos requisitos existentes de força da senha.
- Máscara do telefone comercial, placeholders de loja e suporte a URL ou
  caminho relativo no campo de imagem.
- Catálogo anuncia quantidade de resultados, apresenta skeleton no carregamento
  inicial, mantém estados vazios e agora conecta a ação de limpar filtros.
- Confirmação antes de checkout, cancelamento de pedido e exclusões; estados de
  carregamento, transições sutis e suporte a `prefers-reduced-motion`.
- Ajustes responsivos e estilos consistentes para foco, campos e erros.
- Arquivos alterados: `frontend/index.html`, `frontend/app.js`,
  `frontend/styles.css` e este registro.
- Validação: `node --check frontend/app.js` passou. Navegador local confirmou
  catálogo, estado vazio/busca/limpeza, seleção de vendedor, máscara de
  telefone, alternância de senha sem perda do valor, mensagem de confirmação
  divergente, fechamento de diálogo e header sticky a 390 px sem overflow.
  O `401` de `/auth/me` ao abrir como visitante é esperado. Não foram enviados
  cadastros, pedidos ou alterações ao Redis durante a validação visual.
- A suíte backend não foi repetida nesta etapa, pois não houve alterações no
  backend. Login/cadastro autenticados e fluxos que escrevem no Redis ficam
  pendentes de validação com conta/dados de teste controlados.

### Correção — rolagem ao abrir detalhes do produto

- O foco automático do botão de fechar no diálogo de detalhes podia mover a
  viewport ao abrir/fechar um produto. Agora a interface registra a posição
  atual, foca o botão sem rolagem e restaura a mesma posição ao abrir e fechar.
- Teste no navegador a 390 px: antes, durante e depois do diálogo, `scrollY`
  permaneceu em 938 px; ao fechar, o foco voltou ao produto que foi acionado.
- `node --check frontend\\app.js` passou. Cache atualizado com `linx-scroll-1`.
- Após o relato de que o modal ainda aparecia fora da tela, corrigido também o
  posicionamento CSS que o deixava relativo ao conteúdo. Agora o diálogo de
  detalhes é `fixed`, centralizado no viewport, com altura máxima e rolagem
  interna para telas menores.
- Reteste com a página rolada (390 × 844): diálogo visível e centralizado,
  limites `top=157.6` e `bottom=686.4`, `position=fixed`, rolagem preservada
  em 938 px.
