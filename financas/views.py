import calendar
from datetime import date

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.utils import org_atual, organizacao_requerida, papel_requerido

from .dashboard import ler_periodo, metricas, para_grafico
from .forms import LancamentoForm, OrcamentoForm
from .models import Categoria, Conta, Lancamento, Orcamento, Parcela
from .views_cadastros import _salvar

# Regra de ouro (Aula 14): toda consulta parte de filter(organizacao=org),
# e "org" vem sempre de org_atual(request), nunca da URL ou do formulário.


@organizacao_requerida
def dashboard(request):
    org = org_atual(request)
    eh_admin = request.user.perfil.eh_admin
    hoje = date.today()

    # Métricas do período (todas derivam da mesma base filtrada: org + período).
    form_periodo, inicio, fim = ler_periodo(request.GET)
    dados = metricas(org, inicio, fim, com_serie=eh_admin)

    # Retrato atual (não depende do período): saldos, orçamentos do mês e próximas parcelas.
    contas = Conta.objects.filter(organizacao=org).com_saldo()
    orcamentos_do_mes = (
        Orcamento.objects.filter(organizacao=org, mes=hoje.month, ano=hoje.year)
        .select_related('categoria').com_gasto()
    )
    proximas_parcelas = (
        Parcela.objects.filter(lancamento__organizacao=org, paga=False, lancamento__tipo='despesa')
        .select_related('lancamento').order_by('data_vencimento')[:8]
    )

    return render(request, 'financas/dashboard.html', {
        'form_periodo': form_periodo,
        'inicio': inicio,
        'fim': fim,
        'atalhos': atalhos_de_periodo(hoje),
        'kpis': dados['kpis'],
        'ranking_categorias': dados['ranking_categorias'],
        'distribuicao_contas': dados['distribuicao_contas'],
        'serie_mensal': dados.get('serie_mensal', []),
        'graficos': para_grafico(dados, ids_contas=[c.pk for c in sorted(contas, key=lambda c: c.pk)]),
        # Dashboard por papel (Aula 17): série e exportação só para administradores.
        'mostra_series': eh_admin,
        'contas': contas,
        'saldo_total': sum((conta.saldo_atual for conta in contas), 0),
        'orcamentos_do_mes': orcamentos_do_mes,
        'orcamentos_estourados': sum(1 for o in orcamentos_do_mes if o.estourado),
        'proximas_parcelas': proximas_parcelas,
        'mes_atual': hoje.month,
        'ano_atual': hoje.year,
    })


def atalhos_de_periodo(hoje):
    """Links prontos de período para o filtro do dashboard."""
    ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
    return [
        ('Este mês', f'?inicio={hoje:%Y-%m}-01&fim={hoje:%Y-%m}-{ultimo_dia:02d}'),
        ('Este ano', f'?inicio={hoje.year}-01-01&fim={hoje.year}-12-31'),
        ('Tudo', '?inicio=&fim='),
    ]


@organizacao_requerida
def lancamento_lista(request):
    org = org_atual(request)
    lancamentos = (
        Lancamento.objects.filter(organizacao=org)
        .select_related('conta', 'categoria')
        .prefetch_related('parcelas')
    )

    # Feature 1: busca por descrição + filtro por categoria (podem ser usados juntos ou separados)
    q = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '')

    # Desafio extra: as duas condições são combinadas num único objeto Q() e aplicadas
    # numa só chamada de .filter(). Q() vazio não filtra nada; "&=" junta as condições
    # com AND, então com os dois preenchidos o SQL fica: WHERE descricao LIKE ... AND categoria_id = ...
    filtros = Q()
    if q:
        filtros &= Q(descricao__icontains=q)
    if categoria_id.isdigit():
        filtros &= Q(categoria_id=categoria_id)
    lancamentos = lancamentos.filter(filtros)

    return render(request, 'financas/lancamento_lista.html', {
        'lancamentos': lancamentos,
        'categorias': Categoria.objects.filter(organizacao=org),
        'categoria_id': categoria_id,
        'filtrando': bool(q or categoria_id),
    })


@organizacao_requerida
def lancamento_criar(request):
    org = org_atual(request)
    form = LancamentoForm(request.POST or None, org=org)
    if request.method == 'POST' and form.is_valid():
        # commit=False: o form não tem o campo organizacao; quem define é o usuário logado.
        lancamento = form.save(commit=False)
        lancamento.organizacao = org
        lancamento.save()
        if lancamento.parcelado:
            messages.success(
                request,
                f'Lançamento criado e dividido em {lancamento.numero_parcelas} parcelas automaticamente.',
            )
        else:
            messages.success(request, 'Lançamento criado com sucesso.')
        return redirect('lancamento_lista')
    return render(request, 'financas/lancamento_form.html', {'form': form, 'titulo': 'Novo lançamento'})


@organizacao_requerida
def orcamento_lista(request):
    orcamentos = Orcamento.objects.filter(organizacao=org_atual(request)).select_related('categoria').com_gasto()
    return render(request, 'financas/orcamento_lista.html', {'orcamentos': orcamentos})


@papel_requerido('admin')
def orcamento_criar(request):
    return _salvar(request, OrcamentoForm, 'Orçamento', 'orcamento_lista')


@organizacao_requerida
def parcela_lista(request):
    parcelas = (
        Parcela.objects.filter(lancamento__organizacao=org_atual(request))
        .select_related('lancamento', 'lancamento__categoria')
    )
    return render(request, 'financas/parcela_lista.html', {'parcelas': parcelas})


@require_POST
@organizacao_requerida
def parcela_marcar_paga(request, pk):
    # Com a organização no filtro, o id de uma parcela de outra organização dá 404,
    # como se não existisse (não revela que o registro existe).
    parcela = get_object_or_404(Parcela, pk=pk, lancamento__organizacao=org_atual(request))
    parcela.paga = not parcela.paga
    parcela.save(update_fields=['paga'])
    return redirect('parcela_lista')
