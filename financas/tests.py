"""Testes da P2: isolamento entre organizações, papéis, API, validação e dashboard.

Cenário fixo (números fáceis de conferir à mão):
- Organização A: usuários ana (administradora) e otto (operador);
  3 despesas de R$ 10,00 em setembro/2026 e 1 receita de R$ 100,00.
- Organização B: usuário bia (administradora);
  5 despesas de R$ 10,00 em setembro/2026.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import Organizacao, Perfil

from .dashboard import base_parcelas, metricas
from .models import Categoria, Conta, Lancamento, Orcamento, Parcela

SETEMBRO = date(2026, 9, 10)


class CenarioDuasOrganizacoes(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organizacao.objects.create(nome='Casa A')
        cls.org_b = Organizacao.objects.create(nome='Casa B')

        cls.ana = cls._usuario('ana', cls.org_a, Perfil.ADMIN)
        cls.otto = cls._usuario('otto', cls.org_a, Perfil.OPERADOR)
        cls.bia = cls._usuario('bia', cls.org_b, Perfil.ADMIN)

        cls.conta_a = Conta.objects.create(organizacao=cls.org_a, nome='Banco A', saldo_inicial=0)
        cls.mercado_a = Categoria.objects.create(organizacao=cls.org_a, nome='Mercado', tipo='despesa')
        cls.salario_a = Categoria.objects.create(organizacao=cls.org_a, nome='Salário', tipo='receita')
        cls.conta_b = Conta.objects.create(organizacao=cls.org_b, nome='Banco B', saldo_inicial=0)
        cls.mercado_b = Categoria.objects.create(organizacao=cls.org_b, nome='Mercado', tipo='despesa')

        for i in range(3):
            cls._lancamento(cls.org_a, cls.conta_a, cls.mercado_a, f'Compra A{i}', 10)
        cls._lancamento(cls.org_a, cls.conta_a, cls.salario_a, 'Salário A', 100, tipo='receita')
        for i in range(5):
            cls._lancamento(cls.org_b, cls.conta_b, cls.mercado_b, f'Compra B{i}', 10)
        cls.lancamento_b = Lancamento.objects.filter(organizacao=cls.org_b).first()

    @staticmethod
    def _usuario(nome, org, papel):
        user = User.objects.create_user(nome, password='senha-de-teste-123')
        Perfil.objects.create(usuario=user, organizacao=org, papel=papel)
        return user

    @staticmethod
    def _lancamento(org, conta, categoria, descricao, valor, tipo='despesa', data=SETEMBRO, parcelas=1):
        return Lancamento.objects.create(
            organizacao=org, conta=conta, categoria=categoria, descricao=descricao,
            valor=Decimal(valor), tipo=tipo, data=data,
            parcelado=parcelas > 1, numero_parcelas=parcelas,
        )


class IsolamentoTelasTest(CenarioDuasOrganizacoes):
    """Roteiro de isolamento da Aula 14, automatizado."""

    def setUp(self):
        self.client.force_login(self.ana)

    def test_anonimo_e_redirecionado_para_o_login(self):
        self.client.logout()
        resposta = self.client.get('/lancamentos/')
        self.assertRedirects(resposta, '/auth/login/?next=/lancamentos/')

    def test_lista_mostra_so_lancamentos_da_organizacao(self):
        resposta = self.client.get('/lancamentos/')
        descricoes = {l.descricao for l in resposta.context['lancamentos']}
        self.assertEqual(descricoes, {'Compra A0', 'Compra A1', 'Compra A2', 'Salário A'})

    def test_id_de_outra_organizacao_na_url_da_404(self):
        self.assertEqual(self.client.get(f'/lancamentos/{self.lancamento_b.pk}/editar/').status_code, 404)
        self.assertEqual(self.client.get(f'/contas/{self.conta_b.pk}/editar/').status_code, 404)
        parcela_b = self.lancamento_b.parcelas.first()
        self.assertEqual(self.client.post(f'/parcelas/{parcela_b.pk}/marcar-paga/').status_code, 404)
        parcela_b.refresh_from_db()
        self.assertFalse(parcela_b.paga)

    def test_criacao_grava_na_organizacao_do_usuario(self):
        self.client.post('/lancamentos/novo/', {
            'conta': self.conta_a.pk, 'categoria': self.mercado_a.pk, 'descricao': 'Nova compra',
            'valor': '25.00', 'tipo': 'despesa', 'data': '2026-09-15', 'numero_parcelas': 1,
        })
        self.assertEqual(Lancamento.objects.get(descricao='Nova compra').organizacao, self.org_a)

    def test_selects_do_formulario_so_tem_opcoes_da_organizacao(self):
        form = self.client.get('/lancamentos/novo/').context['form']
        self.assertEqual(list(form.fields['conta'].queryset), [self.conta_a])
        self.assertNotIn(self.mercado_b, form.fields['categoria'].queryset)

    def test_nao_aceita_conta_de_outra_organizacao_no_post(self):
        resposta = self.client.post('/lancamentos/novo/', {
            'conta': self.conta_b.pk, 'categoria': self.mercado_a.pk, 'descricao': 'Invasão',
            'valor': '1.00', 'tipo': 'despesa', 'data': '2026-09-15', 'numero_parcelas': 1,
        })
        self.assertIn('conta', resposta.context['form'].errors)
        self.assertFalse(Lancamento.objects.filter(descricao='Invasão').exists())

    def test_unicidade_de_categoria_e_por_organizacao(self):
        # B já tem "Mercado (Despesa)", mas A pode ter a sua... e já tem: duplicar dentro de A falha.
        resposta = self.client.post('/categorias/nova/', {'nome': 'mercado', 'tipo': 'despesa'})
        self.assertIn('nome', resposta.context['form'].errors)
        # Nome usado só pela organização B é permitido para A.
        Categoria.objects.create(organizacao=self.org_b, nome='Pets', tipo='despesa')
        self.client.post('/categorias/nova/', {'nome': 'Pets', 'tipo': 'despesa'})
        self.assertTrue(Categoria.objects.filter(organizacao=self.org_a, nome='Pets').exists())

    def test_superusuario_sem_perfil_ve_aviso_em_vez_de_erro(self):
        root = User.objects.create_superuser('root', password='senha-de-teste-123')
        self.client.force_login(root)
        resposta = self.client.get('/')
        self.assertEqual(resposta.status_code, 403)
        self.assertTemplateUsed(resposta, 'core/sem_organizacao.html')


class PapeisTest(CenarioDuasOrganizacoes):
    def test_operador_nao_acessa_cadastros_nem_exclusoes(self):
        self.client.force_login(self.otto)
        for url in ['/contas/nova/', f'/contas/{self.conta_a.pk}/editar/', '/categorias/nova/',
                    '/orcamentos/novo/', f'/lancamentos/{Lancamento.objects.filter(organizacao=self.org_a).first().pk}/excluir/',
                    '/dashboard/exportar.csv']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_operador_ve_listas_e_cria_lancamentos(self):
        self.client.force_login(self.otto)
        for url in ['/', '/lancamentos/', '/lancamentos/novo/', '/contas/', '/categorias/', '/parcelas/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_administrador_acessa_cadastros(self):
        self.client.force_login(self.ana)
        for url in ['/contas/nova/', '/categorias/nova/', '/orcamentos/novo/', '/dashboard/exportar.csv']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)


class ApiTest(CenarioDuasOrganizacoes):
    def setUp(self):
        self.api = APIClient()

    def test_api_exige_login(self):
        self.assertEqual(self.api.get('/api/lancamentos/').status_code, 403)

    def test_lista_so_da_organizacao_e_404_para_id_alheio(self):
        self.api.force_authenticate(self.ana)
        self.assertEqual(len(self.api.get('/api/lancamentos/').json()), 4)
        self.assertEqual(self.api.get(f'/api/lancamentos/{self.lancamento_b.pk}/').status_code, 404)

    def test_criacao_usa_organizacao_do_usuario_e_valida_fk(self):
        self.api.force_authenticate(self.ana)
        dados = {'conta': self.conta_a.pk, 'categoria': self.mercado_a.pk, 'descricao': 'Via API',
                 'valor': '30.00', 'tipo': 'despesa', 'data': '2026-09-20', 'parcelado': True, 'numero_parcelas': 3}
        resposta = self.api.post('/api/lancamentos/', dados, format='json')
        self.assertEqual(resposta.status_code, 201)
        criado = Lancamento.objects.get(pk=resposta.json()['id'])
        self.assertEqual(criado.organizacao, self.org_a)
        self.assertEqual(criado.parcelas.count(), 3)

        dados['conta'] = self.conta_b.pk
        self.assertEqual(self.api.post('/api/lancamentos/', dados, format='json').status_code, 400)

    def test_regra_do_valor_vale_na_api(self):
        self.api.force_authenticate(self.ana)
        resposta = self.api.post('/api/lancamentos/', {
            'conta': self.conta_a.pk, 'categoria': self.mercado_a.pk, 'descricao': 'Zero',
            'valor': '0', 'tipo': 'despesa', 'data': '2026-09-20',
        }, format='json')
        self.assertEqual(resposta.status_code, 400)
        self.assertIn('valor', resposta.json())

    def test_permissoes_por_papel_na_api(self):
        lancamento = Lancamento.objects.filter(organizacao=self.org_a).first()
        self.api.force_authenticate(self.otto)
        self.assertEqual(self.api.post('/api/contas/', {'nome': 'X', 'tipo': 'corrente'}, format='json').status_code, 403)
        self.assertEqual(self.api.delete(f'/api/lancamentos/{lancamento.pk}/').status_code, 403)
        self.assertEqual(self.api.patch(f'/api/lancamentos/{lancamento.pk}/', {'descricao': 'Editada'}, format='json').status_code, 200)

        self.api.force_authenticate(self.ana)
        self.assertEqual(self.api.delete(f'/api/lancamentos/{lancamento.pk}/').status_code, 204)

    def test_parcela_so_permite_marcar_como_paga(self):
        parcela = Parcela.objects.filter(lancamento__organizacao=self.org_a).first()
        self.api.force_authenticate(self.otto)
        resposta = self.api.patch(f'/api/parcelas/{parcela.pk}/', {'paga': True, 'valor': '1.00'}, format='json')
        self.assertEqual(resposta.status_code, 200)
        parcela.refresh_from_db()
        self.assertTrue(parcela.paga)
        self.assertEqual(parcela.valor, Decimal('10.00'))  # valor é somente leitura


class LancamentoModelTest(CenarioDuasOrganizacoes):
    def test_valor_deve_ser_maior_que_zero(self):
        lancamento = Lancamento(organizacao=self.org_a, conta=self.conta_a, categoria=self.mercado_a,
                                descricao='x', valor=Decimal('-5'), data=SETEMBRO)
        with self.assertRaises(ValidationError) as erro:
            lancamento.full_clean()
        self.assertIn('valor', erro.exception.message_dict)

    def test_parcelas_somam_o_valor_total(self):
        lancamento = self._lancamento(self.org_a, self.conta_a, self.mercado_a, 'TV', '100.00', parcelas=3)
        valores = list(lancamento.parcelas.values_list('valor', flat=True))
        self.assertEqual(valores, [Decimal('33.33'), Decimal('33.33'), Decimal('33.34')])
        self.assertEqual(sum(valores), Decimal('100.00'))

    def test_editar_valor_refaz_as_parcelas(self):
        lancamento = self._lancamento(self.org_a, self.conta_a, self.mercado_a, 'Sofá', '300.00', parcelas=3)
        lancamento.valor = Decimal('600.00')
        lancamento.save()
        self.assertEqual(list(lancamento.parcelas.values_list('valor', flat=True)), [Decimal('200.00')] * 3)


class DashboardTest(CenarioDuasOrganizacoes):
    """Testes das métricas (Aula 17): se o número está errado, o dashboard mente."""

    def test_totais_sao_so_da_organizacao(self):
        self.client.force_login(self.ana)
        kpis = self.client.get('/?inicio=&fim=').context['kpis']
        self.assertEqual(kpis['despesas'], Decimal('30.00'))  # 3 x 10 (B tem 5 x 10)
        self.assertEqual(kpis['receitas'], Decimal('100.00'))
        self.assertEqual(kpis['resultado'], Decimal('70.00'))

        self.client.force_login(self.bia)
        self.assertEqual(self.client.get('/?inicio=&fim=').context['kpis']['despesas'], Decimal('50.00'))

    def test_periodo_filtra_as_metricas(self):
        self._lancamento(self.org_a, self.conta_a, self.mercado_a, 'Outubro', '40.00', data=date(2026, 10, 5))
        self.client.force_login(self.ana)
        so_setembro = self.client.get('/?inicio=2026-09-01&fim=2026-09-30').context['kpis']
        tudo = self.client.get('/?inicio=&fim=').context['kpis']
        self.assertEqual(so_setembro['despesas'], Decimal('30.00'))
        self.assertEqual(tudo['despesas'], Decimal('70.00'))

    def test_data_invalida_nao_quebra_o_dashboard(self):
        self.client.force_login(self.ana)
        resposta = self.client.get('/?inicio=abc&fim=2026-01-01')
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('inicio', resposta.context['form_periodo'].errors)

    def test_dashboard_vazio_sem_erro(self):
        org = Organizacao.objects.create(nome='Vazia')
        user = self._usuario('vazio', org, Perfil.ADMIN)
        self.client.force_login(user)
        resposta = self.client.get('/')
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context['kpis']['despesas'], 0)
        self.assertContains(resposta, 'Sem despesas no período.')

    def test_serie_e_exportacao_so_para_administrador(self):
        self.client.force_login(self.otto)
        resposta = self.client.get('/')
        self.assertFalse(resposta.context['mostra_series'])
        self.assertNotContains(resposta, 'Exportar CSV')
        self.client.force_login(self.ana)
        self.assertTrue(self.client.get('/').context['mostra_series'])

    def test_ranking_e_serie(self):
        transporte = Categoria.objects.create(organizacao=self.org_a, nome='Transporte', tipo='despesa')
        self._lancamento(self.org_a, self.conta_a, transporte, 'Uber', '50.00')
        dados = metricas(self.org_a)
        self.assertEqual(
            [(r['lancamento__categoria__nome'], r['total']) for r in dados['ranking_categorias']],
            [('Transporte', Decimal('50.00')), ('Mercado', Decimal('30.00'))],
        )
        self.assertEqual(len(dados['serie_mensal']), 1)
        self.assertEqual(dados['serie_mensal'][0]['despesas'], Decimal('80.00'))

    def test_csv_tem_so_parcelas_da_organizacao(self):
        self.client.force_login(self.ana)
        conteudo = self.client.get('/dashboard/exportar.csv?inicio=&fim=').content.decode('utf-8-sig')
        linhas = conteudo.strip().splitlines()
        self.assertEqual(len(linhas), 1 + 4)  # cabeçalho + 4 parcelas de A
        self.assertNotIn('Compra B', conteudo)

    def test_api_do_dashboard(self):
        api = APIClient()
        api.force_authenticate(self.otto)
        dados = api.get('/api/dashboard/?inicio=&fim=').json()
        self.assertEqual(dados['kpis']['despesas'], 30.0)
        self.assertNotIn('serie_mensal', dados)  # operador não vê a série
        self.assertEqual(api.get('/api/dashboard/?inicio=abc').status_code, 400)


class ConsultasTest(CenarioDuasOrganizacoes):
    """Trava o desempenho (Aula 17): o teste falha se o N+1 voltar."""

    def test_saldo_das_contas_numa_consulta(self):
        for i in range(5):
            Conta.objects.create(organizacao=self.org_a, nome=f'Extra {i}')
        with self.assertNumQueries(1):
            saldos = [c.saldo_atual for c in Conta.objects.filter(organizacao=self.org_a).com_saldo()]
        self.assertIn(Decimal('70.00'), saldos)  # Banco A: +100 -30

    def test_gasto_dos_orcamentos_numa_consulta(self):
        for i in range(5):
            categoria = Categoria.objects.create(organizacao=self.org_a, nome=f'Cat {i}', tipo='despesa')
            Orcamento.objects.create(organizacao=self.org_a, categoria=categoria, mes=9, ano=2026, valor_limite=100)
        Orcamento.objects.create(organizacao=self.org_a, categoria=self.mercado_a, mes=9, ano=2026, valor_limite=20)
        with self.assertNumQueries(1):
            orcamentos = list(Orcamento.objects.filter(organizacao=self.org_a).select_related('categoria').com_gasto())
            estourados = [o.categoria.nome for o in orcamentos if o.estourado]
        self.assertEqual(estourados, ['Mercado'])  # gastou 30 de 20

    def test_numero_de_consultas_do_dashboard_nao_cresce_com_os_dados(self):
        self.client.force_login(self.ana)
        self.client.get('/')  # aquece a sessão
        with self.assertNumQueries(11):
            self.client.get('/')
        for i in range(10):
            conta = Conta.objects.create(organizacao=self.org_a, nome=f'Mais {i}')
            self._lancamento(self.org_a, conta, self.mercado_a, f'Mais {i}', 5)
        with self.assertNumQueries(11):
            self.client.get('/')

    def test_base_do_dashboard_parte_da_organizacao(self):
        sql = str(base_parcelas(self.org_a).query)
        self.assertIn('organizacao_id', sql)
