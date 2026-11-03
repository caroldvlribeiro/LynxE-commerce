# Manual de execução e demonstração — Linx

## Preparar ambiente

1. Instale Python 3.11 ou superior no Windows.
2. Na raiz do projeto, crie e ative o ambiente virtual:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

3. Crie `.env` a partir de `.env.example` e preencha com o endpoint e as
   credenciais de teste do Redis Cloud Essentials Free. Não compartilhe nem
   versione esse arquivo.
4. No Windows, execute `iniciar.bat` na raiz do projeto. O script ativa o
   ambiente virtual existente, verifica as dependências e inicia a loja.
   Alternativamente, execute:

   ```powershell
   python -m uvicorn backend.app.main:app --reload
   ```

   O app testa a conexão Redis no startup. A loja fica em
   `http://127.0.0.1:8000`; OpenAPI em `/docs`.

## Roteiro de demonstração

1. Na interface, teste as opções de cadastro **Cliente** e **Vendedor**.
   Para vendedor, informe nome e descrição da loja; telefone é opcional.
   Confira **Meu perfil** nas duas contas.
2. Se precisar provisionar um vendedor administrativamente:

   ```powershell
   python -m backend.app.scripts.create_seller --name "Vendedor de teste" --email "vendedor@example.com"
   ```

3. Como vendedor, teste a edição das informações pessoais e da loja, a
   alteração de senha com senha atual e, em **Gerenciar**, cadastre uma
   categoria e um produto. Edite e exclua somente os próprios produtos.
4. Saia e entre como cliente; confira seus pedidos e a sacola, use
   busca/categoria, adicione produtos à sacola
   e altere as quantidades.
5. Tente exceder o estoque; a API deve recusar a operação. Finalize o pedido
   simulado e mostre a baixa de estoque.
6. Abra **Meus pedidos** e mostre o snapshot de preço do momento da compra.
   Cancele o pedido e verifique a devolução de estoque.
7. Em `/docs`, demonstre as rotas protegidas e respostas HTTP `401`/`403`.

## Testes

Com `.env` configurado para a instância Redis Cloud de teste:

```powershell
python -m pytest -q
```

Os testes de integração escrevem dados temporários e os removem ao final.
Não use dados sensíveis nem credenciais reais de clientes no plano gratuito,
que não oferece TLS.

## Limitações acadêmicas

- O checkout é acadêmico e não realiza pagamento. Sessões são revogáveis no
  Redis; HTTPS e Redis com TLS são necessários para uso real.
- Produtos antigos sem proprietário seguem visíveis se ativos, mas não podem
  ser editados por vendedores até uma atribuição administrativa explícita.
- O carrinho não reserva estoque; disponibilidade é revalidada atomicamente
  ao finalizar.
- Pesquisa textual percorre o catálogo em memória; é adequada à escala da
  demonstração, não a um catálogo de grande porte.
