# Controle Financeiro: de MVP (P1) a mini-SaaS (P2)

Projeto da disciplina **Laboratório de Programação Full Stack** da Universidade de Vassouras.

Sistema de controle financeiro com orçamento por categoria/mês e parcelamento
automático de despesas. Na P2, o mesmo projeto da P1 virou um **mini-SaaS**:
várias organizações (uma família, uma república, um casal...) usam o sistema no
mesmo banco, e cada uma vê só os próprios dados, com papéis de acesso, dashboard
com métricas e gráficos, e uma API REST.

## Entidades

- **Organizacao** (app `core`): o "inquilino", dono dos dados.
- **Perfil** (app `core`): liga o `User` do Django a uma organização e a um papel (administrador ou operador).
- **Conta**: onde o dinheiro está (conta corrente, poupança, carteira, cartão).
- **Categoria**: classificação de receitas e despesas (Alimentação, Transporte, Salário...).
- **Lançamento**: uma movimentação (receita ou despesa), à vista ou parcelada.
- **Parcela**: cada parcela gerada automaticamente a partir de um lançamento, com o seu vencimento.
- **Orçamento**: limite de gasto de uma categoria num mês/ano.

Conta, Categoria, Lançamento e Orçamento herdam da base abstrata `DaOrganizacao`
(FK obrigatória para `Organizacao`). A Parcela é isolada pelo lançamento (`lancamento__organizacao`).

## O que a P2 entrega (os quatro pilares)

### 1. Multi-organização (Aula 14)

- Estratégia de **coluna discriminadora**: todos os dados no mesmo banco, com FK para a organização.
- Toda consulta parte de `filter(organizacao=org_atual(request))`. A organização vem
  **sempre do usuário logado**, nunca da URL nem do formulário (`core/utils.py`).
- `get_object_or_404(..., organizacao=org)`: um id de outra organização na URL dá **404**.
- Criação com `form.save(commit=False)` + `obj.organizacao = org`.
- Selects de conta e categoria filtrados pela organização (nos forms e nos serializers).
- Unicidade **por organização**: `UniqueConstraint(organizacao, nome, tipo)` em Categoria.
- Migração **sem perder os dados da P1**, em 3 etapas: FK opcional (`0002`) → `RunPython`
  que cria a "Organização padrão" e preenche os registros antigos (`0003`) → FK obrigatória (`0004`).
- Superusuário sem perfil vê uma página explicando o que falta, em vez de erro 500.

### 2. Perfis de acesso (Aula 15)

| Ação | Administrador | Operador |
|---|:---:|:---:|
| Ver dashboard, lançamentos, parcelas, contas, categorias, orçamentos | ✔ | ✔ |
| Criar e editar lançamentos, marcar parcela como paga | ✔ | ✔ |
| Excluir lançamentos | ✔ | ✘ |
| Criar, editar e excluir contas, categorias e orçamentos | ✔ | ✘ |
| Série mensal do dashboard e exportação CSV | ✔ | ✘ |

Nas telas: decorator `@papel_requerido('admin')` (responde 403) e botões escondidos para quem não pode usá-los.
Na API: as permissões `EhAdminOuSomenteLeitura`, `SomenteAdminExclui` e `EhAdmin` (`core/permissions.py`).

### 3. Dashboard (Aula 17)

As métricas ficam em `financas/dashboard.py` e partem todas da mesma base: as parcelas
da organização no período, pela data de vencimento (regime de caixa).

| Pergunta do dono | Métrica | Como é calculada | Visual |
|---|---|---|---|
| Quanto entrou, saiu e sobrou? | KPIs | `aggregate` com `Sum(filter=Q(...))` numa consulta | cartões |
| Onde eu mais gasto? | ranking de categorias | `values` + `annotate` + `order_by` + `[:5]` | barras horizontais |
| Como evolui mês a mês? | série temporal | `TruncMonth` + `annotate` + `order_by('mes')` | barras agrupadas (só admin) |
| De qual conta sai o dinheiro? | distribuição | `values` + `annotate` por conta | rosca |

- Filtro por período com `PeriodoForm`: uma data inválida na URL não gera erro 500.
  Atalhos "Este mês", "Este ano" e "Tudo"; sem filtro, mostra o ano corrente.
- Gráficos com **Chart.js**: os dados vão para a página com `json_script`, e o JS fica em
  `financas/static/financas/js/dashboard.js`. As tabelas continuam na página.
- **Exportar CSV** (`/dashboard/exportar.csv`, só admin): usa a mesma base e o mesmo período.
  Sai no formato do Excel em português (`;` e vírgula decimal) e é protegido contra injeção de fórmula.

### 4. API REST com DRF (Aulas 13 e 16)

Todos os endpoints exigem login (`IsAuthenticated` + `TemOrganizacao`) e filtram pela organização.
A raiz navegável fica em **`/api/`**, e o login da Browsable API em `/api-auth/login/`.

| Endpoint | Métodos | Observações |
|---|---|---|
| `/api/contas/` | GET, POST, PUT, PATCH, DELETE | inclui `saldo_atual`; só admin altera |
| `/api/categorias/` | GET, POST, PUT, PATCH, DELETE | só admin altera; excluir categoria em uso → 409 |
| `/api/lancamentos/` | GET, POST, PUT, PATCH, DELETE | gera as parcelas; `?q=` e `?categoria=`; só admin exclui |
| `/api/parcelas/` | GET, PATCH | só o campo `paga` é editável |
| `/api/orcamentos/` | GET, POST, PUT, PATCH, DELETE | inclui `valor_gasto`, `percentual_usado` e `estourado` |
| `/api/dashboard/` | GET | métricas do dashboard; `?inicio=AAAA-MM-DD&fim=AAAA-MM-DD` |

A regra de negócio fica **num lugar só**: `Lancamento.clean()` (valor > 0, parcelas, conta e
categoria da mesma organização). O form, o Admin e o serializer chamam essa mesma validação,
e na API o erro vira uma resposta 400 em JSON.

A API aceita a sessão do navegador (a mesma das telas, como pede a Aula 13) e a autenticação
Basic, que é padrão do DRF e serve para testar no terminal:

```bash
curl -u ana:demo12345 "http://127.0.0.1:8000/api/lancamentos/?q=mercado"
curl -u ana:demo12345 "http://127.0.0.1:8000/api/dashboard/?inicio=2026-01-01&fim=2026-12-31"
```

## Stack

- Python 3.11+ e Django 5
- Django REST Framework
- SQLite (roda localmente sem instalar servidor de banco)
- python-dotenv (`SECRET_KEY` e `DEBUG` fora do código-fonte)
- Bootstrap e Chart.js via CDN

## Como rodar localmente

```powershell
# 1. criar e ativar o ambiente virtual
python -m venv venv
venv\Scripts\activate

# 2. instalar as dependências
pip install -r requirements.txt

# 3. copiar o arquivo de variáveis de ambiente (e trocar a SECRET_KEY)
copy .env.example .env

# 4. criar as tabelas
python manage.py migrate

# 5. criar os dados de demonstração (2 organizações, 3 usuários, 6 meses de dados)
python manage.py popular_demo

# 6. (opcional) superusuário para o Django Admin
python manage.py createsuperuser

# 7. rodar o servidor
python manage.py runserver
```

Acesse **http://127.0.0.1:8000/** e entre com um dos usuários de demonstração:

| Usuário | Senha | Organização | Papel |
|---|---|---|---|
| `ana` | `demo12345` | Família Souza | Administrador |
| `otto` | `demo12345` | Família Souza | Operador |
| `bia` | `demo12345` | República Vassouras | Administrador |

Para refazer os dados de demonstração: `python manage.py popular_demo --recriar`.

O superusuário criado com `createsuperuser` não tem perfil. Ele usa o **Django Admin**
(`/admin/`), onde enxerga todas as organizações e pode criar organizações, usuários e perfis.

## Testes

```powershell
python manage.py test
```

São 36 testes (`financas/tests.py` e `core/tests.py`), todos com duas organizações e números fáceis de
conferir à mão (3 despesas de R$ 10 na organização A e 5 na B). Eles cobrem:

- o roteiro de isolamento da Aula 14 (tabela abaixo);
- os papéis (operador recebe 403 em cadastros, exclusões e exportação);
- a API (login, filtro por organização, validação do model, permissões, PATCH de parcela);
- as métricas do dashboard (total por organização, período, data inválida, dashboard vazio, CSV);
- `assertNumQueries` travando os N+1 corrigidos.

### Roteiro de isolamento (Aula 14): resultado

Executado com dois usuários de organizações diferentes, manualmente e nos testes automáticos:

| Cenário | Esperado | Resultado |
|---|---|---|
| Usuário A abre a lista de lançamentos | vê só os da organização A | ✔ |
| Usuário A abre `/lancamentos/<id da B>/editar/` | 404 | ✔ |
| Usuário A marca como paga uma parcela da B | 404 (parcela não muda) | ✔ |
| Usuário A cria um lançamento | gravado com a organização A | ✔ |
| Formulário do usuário A | selects só com contas e categorias de A | ✔ |
| Usuário A envia o id de uma conta da B no POST | erro de validação | ✔ |
| Usuário A cria categoria com nome usado só pela B | permitido (unicidade por organização) | ✔ |
| API: usuário A pede `/api/lancamentos/<id da B>/` | 404 | ✔ |
| Dashboard e CSV do usuário A | nenhum número da B | ✔ |

### Desempenho (N+1)

Medido com `CaptureQueriesContext`, com 10 contas e 10 orçamentos no mês:

| Tela | Antes | Depois |
|---|---:|---:|
| Dashboard | 99 consultas | 11 |
| Orçamentos | 71 | 5 |
| Contas | 29 | 5 |
| API de contas | 25 | 1 |
| API de orçamentos | 34 | 1 |

A correção usa `Conta.objects.com_saldo()` (`Sum` com `filter=` numa consulta) e
`Orcamento.objects.com_gasto()` (`Subquery` correlacionada), mais `select_related`. Há também índices em
`Parcela.data_vencimento` e `Lancamento(organizacao, data)`.

## Documentos do projeto

- [`MELHORIAS_P1.md`](MELHORIAS_P1.md): revisão da P1 feita antes da P2 e o que foi corrigido.
- [`BACKLOG_P2.md`](BACKLOG_P2.md): backlog da P2 organizado pelos quatro pilares.

## Estrutura do projeto

```
financeiro/                 # configurações (settings, urls)
core/                       # Organizacao, Perfil, DaOrganizacao, org_atual, papéis e permissões da API
financas/
  models.py                 # Conta, Categoria, Lancamento, Parcela, Orcamento
  views.py                  # dashboard, lançamentos, parcelas, exportação CSV
  views_cadastros.py        # CRUD de contas, categorias, lançamentos e orçamentos
  dashboard.py              # métricas do dashboard (reaproveitadas pela tela, CSV e API)
  serializers.py            # serializers do DRF
  api_views.py, api_urls.py # API REST (ViewSets + router)
  management/commands/      # popular_demo
  static/financas/js/       # gráficos (Chart.js)
  tests.py
manage.py
requirements.txt
.env.example
```
