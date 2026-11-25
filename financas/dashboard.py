"""Métricas do dashboard, calculadas pelo ORM.

Perguntas do dono do sistema (Aula 17, "comece pela pergunta, não pela tela"):

1. Quanto entrou, quanto saiu e quanto sobrou no período?   -> KPIs (aggregate)
2. Em que categorias eu mais gasto?                          -> ranking (values + annotate + order_by)
3. Como receitas e despesas evoluem mês a mês?              -> série temporal (TruncMonth)
4. De qual conta/cartão está saindo o dinheiro?              -> distribuição por conta

Todas partem da MESMA base: as parcelas da organização do usuário, filtradas
pelo período. Usamos a data de vencimento das parcelas (regime de caixa): uma
compra de R$ 900 em 3x conta R$ 300 em cada mês em que a parcela vence.

As funções ficam aqui (e não na view) para serem reaproveitadas pela tela,
pela exportação CSV e pela API do dashboard, sem duplicar consultas.
"""

from datetime import date

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth

from .forms import PeriodoForm
from .models import DINHEIRO, ZERO, Parcela

RECEITA = Q(lancamento__tipo='receita')
DESPESA = Q(lancamento__tipo='despesa')


def periodo_padrao(hoje=None):
    """Sem filtro na URL, o dashboard mostra o ano corrente."""
    hoje = hoje or date.today()
    return date(hoje.year, 1, 1), date(hoje.year, 12, 31)


def ler_periodo(dados_get):
    """Lê ?inicio=&fim= com um Form (nunca confie na data digitada na URL).

    - sem parâmetros: período padrão (ano corrente);
    - ?inicio=&fim= vazios: todo o histórico;
    - datas inválidas ("abc"): o form acusa o erro e cai no período padrão,
      em vez de estourar erro 500.
    Devolve (form, inicio, fim).
    """
    if 'inicio' not in dados_get and 'fim' not in dados_get:
        inicio, fim = periodo_padrao()
        return PeriodoForm(initial={'inicio': inicio, 'fim': fim}), inicio, fim

    form = PeriodoForm(dados_get)
    if form.is_valid():
        return form, form.cleaned_data['inicio'], form.cleaned_data['fim']
    inicio, fim = periodo_padrao()
    return form, inicio, fim


def base_parcelas(org, inicio=None, fim=None):
    """A base de toda métrica: parcelas da organização, no período.

    O filtro lancamento__organizacao=org é a primeira linha: esquecer =
    dado de outra organização no gráfico.
    """
    qs = Parcela.objects.filter(lancamento__organizacao=org)
    if inicio:
        qs = qs.filter(data_vencimento__gte=inicio)
    if fim:
        qs = qs.filter(data_vencimento__lte=fim)
    return qs


def kpis(base):
    """Vários totais em UMA consulta (aggregate com filter=)."""
    totais = base.aggregate(
        receitas=Coalesce(Sum('valor', filter=RECEITA), ZERO),
        despesas=Coalesce(Sum('valor', filter=DESPESA), ZERO),
        parcelas_em_aberto=Count('id', filter=DESPESA & Q(paga=False)),
        valor_em_aberto=Coalesce(Sum('valor', filter=DESPESA & Q(paga=False)), ZERO),
    )
    totais['resultado'] = totais['receitas'] - totais['despesas']
    return totais


def ranking_categorias(base, limite=5):
    """Top N categorias de despesa: agrupa, soma, ordena do maior e fatia."""
    return list(
        base.filter(DESPESA)
        .values('lancamento__categoria__nome')
        .annotate(total=Sum('valor'))
        .order_by('-total')[:limite]
    )


def serie_mensal(base):
    """Receitas e despesas por mês (TruncMonth), sempre com order_by no fim."""
    linhas = (
        base.annotate(mes=TruncMonth('data_vencimento'))
        .values('mes')
        .annotate(
            receitas=Coalesce(Sum('valor', filter=RECEITA), ZERO, output_field=DINHEIRO),
            despesas=Coalesce(Sum('valor', filter=DESPESA), ZERO, output_field=DINHEIRO),
        )
        .order_by('mes')
    )
    return list(linhas)


def distribuicao_por_conta(base):
    """Fatias das despesas por conta (poucas fatias: boa para rosca/pizza)."""
    return list(
        base.filter(DESPESA)
        .values('lancamento__conta__nome')
        .annotate(total=Sum('valor'))
        .order_by('-total')
    )


def metricas(org, inicio=None, fim=None, com_serie=True):
    """Reúne as quatro métricas. A série é só para administradores (Aula 17)."""
    base = base_parcelas(org, inicio, fim)
    dados = {
        'kpis': kpis(base),
        'ranking_categorias': ranking_categorias(base),
        'distribuicao_contas': distribuicao_por_conta(base),
    }
    if com_serie:
        dados['serie_mensal'] = serie_mensal(base)
    return dados


def para_grafico(dados):
    """Converte para tipos que o JavaScript entende (texto e número).

    O mês vira "MM/AAAA" para servir de rótulo do eixo; Decimal vira float.
    """
    return {
        'ranking': [
            {'rotulo': r['lancamento__categoria__nome'], 'total': float(r['total'])}
            for r in dados['ranking_categorias']
        ],
        'distribuicao': [
            {'rotulo': r['lancamento__conta__nome'], 'total': float(r['total'])}
            for r in dados['distribuicao_contas']
        ],
        'serie': [
            {'mes': r['mes'].strftime('%m/%Y'), 'receitas': float(r['receitas']), 'despesas': float(r['despesas'])}
            for r in dados.get('serie_mensal', [])
        ],
    }
