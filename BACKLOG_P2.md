# Backlog da P2

Os quatro pilares da P2 (Aula 13) quebrados em tarefas, cada uma menor que uma sessão de aula.
Cada tarefa é uma **issue no GitHub** (#1 a #20) com o rótulo do pilar (`melhorias-p1`,
`multi-org`, `perfis`, `api`, `dashboard`), fechada com o commit que a entregou.
Veja em: https://github.com/HerlonSky/p1garridao/issues?q=is%3Aissue

## Revisão da P1

- [x] `MELHORIAS_P1.md` com os pontos frágeis da P1 (`docs: adiciona MELHORIAS_P1.md`)
- [x] Regra do valor > 0 no model e marcar parcela só via POST (`refactor: regra do valor > 0 no model`)
- [x] CRUD completo nas telas (`feat: CRUD completo nas telas`)
- [x] Remover N+1 de saldos e orçamentos (`perf: remove consultas N+1`)

## Pilar 1: multi-organização (`multi-org`)

- [x] App `core` com `Organizacao`, `Perfil` e a base abstrata `DaOrganizacao`
- [x] FK de organização em Conta, Categoria, Lançamento e Orçamento, com migração em 3 etapas
- [x] `org_atual()` e `@organizacao_requerida`; filtro por organização em todas as views
- [x] `get_object_or_404` com a organização; criação com `commit=False`
- [x] Selects dos formulários filtrados pela organização
- [x] Unicidade de categoria por organização
- [x] Roteiro de isolamento executado e registrado no README

## Pilar 2: perfis de acesso (`perfis`)

- [x] Campo `papel` (administrador/operador) no `Perfil`
- [x] `@papel_requerido('admin')` nas telas de cadastro e exclusão
- [x] Botões escondidos conforme o papel; papel exibido na navbar
- [x] Permissões por papel na API

## Pilar 3: API REST (`api`)

- [x] DRF instalado e versionado
- [x] Primeira API (lançamentos) com generics
- [x] API completa com ViewSets e router: contas, categorias, lançamentos, parcelas e orçamentos
- [x] Validação do model reaproveitada no serializer (um lugar só para cada regra)
- [x] Testes da API

## Pilar 4: dashboard (`dashboard`)

- [x] Quatro métricas em `dashboard.py` (KPI, ranking, série e distribuição)
- [x] Filtro por período validado com `PeriodoForm`
- [x] Gráficos com Chart.js e `json_script`
- [x] Exportação CSV (só administrador)
- [x] API do dashboard
- [x] Testes das métricas e `assertNumQueries`

## Próximos passos (fora do escopo entregue)

- [ ] Autenticação por token/JWT na API (Aula 18)
- [ ] Migrar para PostgreSQL e preparar a implantação (Aula 19)
- [ ] Convite de novos usuários para a organização pela própria tela (hoje é pelo Admin)
