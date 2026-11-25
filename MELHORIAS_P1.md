# Melhorias da P1

Revisão do MVP entregue na P1, feita antes de começar a P2 (Aula 13).
A ideia é corrigir o que ficou frágil, porque tudo o que a API expuser
herda o que o model já faz.

## 1. Nenhuma tela exige login

Todas as views (`dashboard`, `lancamento_lista`, `lancamento_criar` etc.) abrem
sem autenticação. Qualquer pessoa com o endereço do sistema vê e altera os dados.

**Correção:** `@login_required` em todas as views, telas de login/logout e
`IsAuthenticated` como permissão padrão da API.

## 2. `parcela_marcar_paga` aceita GET

O template usa um formulário POST, mas a view não confere o método: abrir
`/parcelas/5/marcar-paga/` no navegador já altera o status da parcela.
Uma ação que muda dados não pode ser disparada por um simples link.

**Correção:** `@require_POST` na view.

## 3. Regra do valor > 0 está no form, não no model

A validação "valor do lançamento maior que zero" está em `LancamentoForm.clean_valor()`.
Ela vale nas telas e no Admin (que reaproveita o form), mas **não vale na API**,
porque o serializer não usa o form. A Aula 13 pede um lugar principal para cada regra.

**Correção:** mover a regra para `Lancamento.clean()` (model). O form e o serializer
passam a chamar a mesma validação.

## 4. Consultas N+1 no dashboard e nos orçamentos

- `Conta.saldo_atual` faz 2 consultas por conta (receitas e despesas).
- `Orcamento.valor_gasto` faz 1 consulta por orçamento, e o template chama
  `valor_gasto`, `percentual_usado` e `estourado` (que repetem a consulta).

Com poucas contas não aparece, mas cresce com o número de registros.

**Correção:** calcular os totais com `annotate()` numa única consulta e
reaproveitar o valor já calculado nas propriedades.

## 5. CRUD incompleto nas telas

Pelas telas só dá para **criar** lançamentos e orçamentos. Contas e categorias
só existem no Admin, e editar/excluir só pelo Admin. Com multi-organização, o
usuário comum não vai usar o Admin, então precisa conseguir gerenciar os
próprios dados.

**Correção:** telas de contas e categorias e ações de editar/excluir,
sempre filtradas pela organização do usuário.
