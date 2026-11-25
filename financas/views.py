from datetime import date

from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.utils import org_atual, organizacao_requerida

from .forms import LancamentoForm, OrcamentoForm
from .models import Categoria, Conta, Lancamento, Orcamento, Parcela
from .views_cadastros import _salvar

# Regra de ouro (Aula 14): toda consulta parte de filter(organizacao=org),
# e "org" vem sempre de org_atual(request), nunca da URL ou do formulário.


@organizacao_requerida
def dashboard(request):
    org = org_atual(request)
    hoje = date.today()
    contas = Conta.objects.filter(organizacao=org)
    orcamentos_do_mes = (
        Orcamento.objects.filter(organizacao=org, mes=hoje.month, ano=hoje.year).select_related('categoria')
    )
    lancamentos = Lancamento.objects.filter(organizacao=org)
    parcelas = Parcela.objects.filter(lancamento__organizacao=org)
    parcelas_em_aberto_qs = parcelas.filter(paga=False).select_related('lancamento').order_by('data_vencimento')

    saldo_total = sum((conta.saldo_atual for conta in contas), 0)

    receitas_mes = lancamentos.filter(
        tipo='receita', data__year=hoje.year, data__month=hoje.month,
    ).aggregate(total=Sum('valor'))['total'] or 0

    despesas_mes = parcelas.filter(
        lancamento__tipo='despesa', data_vencimento__year=hoje.year, data_vencimento__month=hoje.month,
    ).aggregate(total=Sum('valor'))['total'] or 0

    return render(request, 'financas/dashboard.html', {
        'contas': contas,
        'orcamentos_do_mes': orcamentos_do_mes,
        'ultimos_lancamentos': lancamentos.select_related('conta', 'categoria')[:10],
        'parcelas_em_aberto': parcelas_em_aberto_qs[:10],
        'mes_atual': hoje.month,
        'ano_atual': hoje.year,
        'saldo_total': saldo_total,
        'receitas_mes': receitas_mes,
        'despesas_mes': despesas_mes,
        'total_parcelas_em_aberto': parcelas_em_aberto_qs.count(),
        'orcamentos_estourados': sum(1 for o in orcamentos_do_mes if o.estourado),
    })


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
    orcamentos = Orcamento.objects.filter(organizacao=org_atual(request)).select_related('categoria')
    return render(request, 'financas/orcamento_lista.html', {'orcamentos': orcamentos})


@organizacao_requerida
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
