"""Cria dados de demonstração: 2 organizações, 3 usuários e 6 meses de movimentação.

Uso:
    python manage.py popular_demo           # cria (se ainda não existir)
    python manage.py popular_demo --recriar # apaga as organizações de demo e cria de novo

As datas são relativas a hoje, então o dashboard sempre tem dados no mês atual.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Organizacao, Perfil
from financas.models import Categoria, Conta, Lancamento, Orcamento, Parcela, somar_meses

SENHA_DEMO = 'demo12345'

ORGANIZACOES = {
    'Família Souza': {
        'usuarios': [('ana', Perfil.ADMIN, 'Ana'), ('otto', Perfil.OPERADOR, 'Otto')],
        'contas': [('Nubank', 'corrente', '2500.00'), ('Carteira', 'carteira', '150.00'),
                   ('Cartão Inter', 'cartao', '0.00')],
        'receitas': [('Salário', 'Salário', 'Nubank', '4200.00'), ('Freela', 'Freela de design', 'Nubank', '650.00')],
        'despesas_mensais': [
            ('Moradia', 'Aluguel', 'Nubank', '1400.00'),
            ('Alimentação', 'Mercado do mês', 'Cartão Inter', '780.00'),
            ('Transporte', 'Combustível', 'Cartão Inter', '260.00'),
            ('Alimentação', 'Feira e padaria', 'Carteira', '120.00'),
            ('Lazer', 'Streaming e cinema', 'Cartão Inter', '95.00'),
        ],
        'parceladas': [
            ('Lazer', 'Notebook novo', 'Cartão Inter', '3600.00', 10, 4),
            ('Saúde', 'Tratamento dentário', 'Nubank', '1200.00', 4, 2),
        ],
        'orcamentos': [('Alimentação', '850.00'), ('Lazer', '300.00'), ('Transporte', '400.00')],
    },
    'República Vassouras': {
        'usuarios': [('bia', Perfil.ADMIN, 'Bia')],
        'contas': [('Caixinha da casa', 'carteira', '300.00'), ('Conta conjunta', 'corrente', '900.00')],
        'receitas': [('Rateio', 'Rateio dos moradores', 'Conta conjunta', '2400.00')],
        'despesas_mensais': [
            ('Moradia', 'Aluguel da república', 'Conta conjunta', '1800.00'),
            ('Contas da casa', 'Luz, água e internet', 'Conta conjunta', '420.00'),
            ('Alimentação', 'Compras coletivas', 'Caixinha da casa', '350.00'),
        ],
        'parceladas': [('Contas da casa', 'Geladeira nova', 'Conta conjunta', '2700.00', 6, 3)],
        'orcamentos': [('Alimentação', '400.00'), ('Contas da casa', '500.00')],
    },
}


class Command(BaseCommand):
    help = 'Cria organizações, usuários e lançamentos de demonstração.'

    def add_arguments(self, parser):
        parser.add_argument('--recriar', action='store_true', help='Apaga os dados de demo antes de criar.')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['recriar']:
            self._apagar()
        elif Organizacao.objects.filter(nome__in=ORGANIZACOES).exists():
            self.stdout.write(self.style.WARNING('Dados de demo já existem. Use --recriar para refazer.'))
            return

        hoje = date.today()
        inicio = date(hoje.year, hoje.month, 1)
        meses = [somar_meses(inicio, -i) for i in range(5, -1, -1)]  # 6 meses, do mais antigo até o atual

        for nome_org, cfg in ORGANIZACOES.items():
            org = Organizacao.objects.create(nome=nome_org)
            for username, papel, primeiro_nome in cfg['usuarios']:
                user = User.objects.create_user(username, password=SENHA_DEMO, first_name=primeiro_nome)
                Perfil.objects.create(usuario=user, organizacao=org, papel=papel)

            contas = {
                nome: Conta.objects.create(organizacao=org, nome=nome, tipo=tipo, saldo_inicial=Decimal(saldo))
                for nome, tipo, saldo in cfg['contas']
            }
            categorias = {}

            def categoria(nome, tipo):
                if (nome, tipo) not in categorias:
                    categorias[(nome, tipo)] = Categoria.objects.create(organizacao=org, nome=nome, tipo=tipo)
                return categorias[(nome, tipo)]

            def lancar(cat, descricao, conta, valor, tipo, data, parcelas=1):
                Lancamento.objects.create(
                    organizacao=org, conta=contas[conta], categoria=categoria(cat, tipo), descricao=descricao,
                    valor=Decimal(valor), tipo=tipo, data=data, parcelado=parcelas > 1, numero_parcelas=parcelas,
                )

            for i, mes in enumerate(meses):
                variacao = Decimal(1) + Decimal(i % 3 - 1) / 10  # meses um pouco diferentes: -10%, 0, +10%
                for cat, descricao, conta, valor in cfg['receitas']:
                    if cat == 'Freela' and i % 2:
                        continue  # freela não acontece todo mês
                    lancar(cat, descricao, conta, valor, 'receita', mes.replace(day=5))
                for dia, (cat, descricao, conta, valor) in enumerate(cfg['despesas_mensais'], start=8):
                    lancar(cat, descricao, conta, (Decimal(valor) * variacao).quantize(Decimal('0.01')),
                           'despesa', mes.replace(day=dia))

            for cat, descricao, conta, valor, n_parcelas, meses_atras in cfg['parceladas']:
                lancar(cat, descricao, conta, valor, 'despesa', somar_meses(inicio, -meses_atras).replace(day=15), n_parcelas)

            # Parcelas que já venceram (antes de hoje) ficam como pagas.
            Parcela.objects.filter(lancamento__organizacao=org, data_vencimento__lt=hoje).update(paga=True)

            for cat, limite in cfg['orcamentos']:
                Orcamento.objects.create(organizacao=org, categoria=categoria(cat, 'despesa'),
                                         mes=hoje.month, ano=hoje.year, valor_limite=Decimal(limite))

            self.stdout.write(f'  {nome_org}: {Lancamento.objects.filter(organizacao=org).count()} lançamentos')

        self.stdout.write(self.style.SUCCESS(
            f'Pronto! Usuários: ana (admin) e otto (operador) na Família Souza; '
            f'bia (admin) na República Vassouras. Senha de todos: {SENHA_DEMO}'
        ))

    def _apagar(self):
        orgs = Organizacao.objects.filter(nome__in=ORGANIZACOES)
        Lancamento.objects.filter(organizacao__in=orgs).delete()
        Orcamento.objects.filter(organizacao__in=orgs).delete()
        Categoria.objects.filter(organizacao__in=orgs).delete()
        Conta.objects.filter(organizacao__in=orgs).delete()
        User.objects.filter(perfil__organizacao__in=orgs).delete()
        orgs.delete()
