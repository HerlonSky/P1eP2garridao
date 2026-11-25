"""Telas de cadastro (criar, editar, excluir) dos dados de cada organização.

Melhoria 5 do MELHORIAS_P1.md: antes só dava para criar pelas telas, e
editar/excluir só pelo Admin. Com multi-organização o usuário comum não usa o
Admin, então as telas precisam cobrir o CRUD completo.

Papéis (Aula 15): cadastros de contas, categorias e orçamentos e qualquer
exclusão são exclusivos de administradores (@papel_requerido('admin')).
Operadores veem as listas e criam/editam lançamentos.

Todas as funções recebem o objeto já buscado com a organização do usuário
(get_object_or_404 com organizacao=org), então um id de outra organização dá 404.
"""

from django.contrib import messages
from django.db.models import Count, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from core.utils import org_atual, organizacao_requerida, papel_requerido

from .forms import CategoriaForm, ContaForm, LancamentoForm, OrcamentoForm
from .models import Categoria, Conta, Lancamento, Orcamento


def _salvar(request, form_class, titulo, voltar_para, instance=None, template='financas/form_generico.html'):
    """Fluxo padrão de criar/editar, sempre gravando na organização do usuário."""
    org = org_atual(request)
    form = form_class(request.POST or None, instance=instance, org=org)
    if request.method == 'POST' and form.is_valid():
        objeto = form.save(commit=False)
        objeto.organizacao = org  # vem do usuário logado, nunca do formulário
        objeto.save()
        messages.success(request, f'{titulo} salvo(a) com sucesso.' if instance is None else 'Alterações salvas.')
        return redirect(voltar_para)
    return render(request, template, {
        'form': form,
        'titulo': f'{"Novo(a)" if instance is None else "Editar"} {titulo.lower()}',
        'voltar_para': voltar_para,
    })


def _excluir(request, objeto, voltar_para, aviso=''):
    """Confirma (GET) e exclui (POST). Trata registros protegidos por PROTECT."""
    if request.method == 'POST':
        try:
            objeto.delete()
            messages.success(request, 'Registro excluído.')
        except ProtectedError:
            messages.error(request, f'Não dá para excluir "{objeto}": há lançamentos ou orçamentos usando este registro.')
        return redirect(voltar_para)
    return render(request, 'financas/confirmar_exclusao.html', {
        'objeto': objeto, 'aviso': aviso, 'voltar_para': voltar_para,
    })


# ---------- Contas ----------

@organizacao_requerida
def conta_lista(request):
    contas = Conta.objects.filter(organizacao=org_atual(request))
    return render(request, 'financas/conta_lista.html', {'contas': contas})


@papel_requerido('admin')
def conta_criar(request):
    return _salvar(request, ContaForm, 'Conta', 'conta_lista')


@papel_requerido('admin')
def conta_editar(request, pk):
    conta = get_object_or_404(Conta, pk=pk, organizacao=org_atual(request))
    return _salvar(request, ContaForm, 'Conta', 'conta_lista', instance=conta)


@papel_requerido('admin')
def conta_excluir(request, pk):
    conta = get_object_or_404(Conta, pk=pk, organizacao=org_atual(request))
    qtd = conta.lancamentos.count()
    aviso = f'Esta conta tem {qtd} lançamento(s), que também serão excluídos.' if qtd else ''
    return _excluir(request, conta, 'conta_lista', aviso)


# ---------- Categorias ----------

@organizacao_requerida
def categoria_lista(request):
    categorias = (
        Categoria.objects.filter(organizacao=org_atual(request))
        .annotate(qtd_lancamentos=Count('lancamentos'))
    )
    return render(request, 'financas/categoria_lista.html', {'categorias': categorias})


@papel_requerido('admin')
def categoria_criar(request):
    return _salvar(request, CategoriaForm, 'Categoria', 'categoria_lista')


@papel_requerido('admin')
def categoria_editar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk, organizacao=org_atual(request))
    return _salvar(request, CategoriaForm, 'Categoria', 'categoria_lista', instance=categoria)


@papel_requerido('admin')
def categoria_excluir(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk, organizacao=org_atual(request))
    return _excluir(request, categoria, 'categoria_lista')


# ---------- Lançamentos e orçamentos (editar/excluir) ----------

@organizacao_requerida
def lancamento_editar(request, pk):
    lancamento = get_object_or_404(Lancamento, pk=pk, organizacao=org_atual(request))
    return _salvar(
        request, LancamentoForm, 'Lançamento', 'lancamento_lista',
        instance=lancamento, template='financas/lancamento_form.html',
    )


@papel_requerido('admin')
def lancamento_excluir(request, pk):
    lancamento = get_object_or_404(Lancamento, pk=pk, organizacao=org_atual(request))
    aviso = f'As {lancamento.numero_parcelas} parcelas também serão excluídas.' if lancamento.parcelado else ''
    return _excluir(request, lancamento, 'lancamento_lista', aviso)


@papel_requerido('admin')
def orcamento_editar(request, pk):
    orcamento = get_object_or_404(Orcamento, pk=pk, organizacao=org_atual(request))
    return _salvar(request, OrcamentoForm, 'Orçamento', 'orcamento_lista', instance=orcamento)


@papel_requerido('admin')
def orcamento_excluir(request, pk):
    orcamento = get_object_or_404(Orcamento, pk=pk, organizacao=org_atual(request))
    return _excluir(request, orcamento, 'orcamento_lista')
