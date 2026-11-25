"""Ponto único que define "de qual organização é este usuário".

Regra de ouro da Aula 14: toda consulta do sistema parte de
filter(organizacao=org_atual(request)). A organização vem SEMPRE do usuário
logado, nunca da URL nem do formulário.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render


def perfil_do_usuario(user):
    """Devolve o Perfil do usuário, ou None (ex.: superusuário criado sem perfil)."""
    if not user.is_authenticated:
        return None
    try:
        return user.perfil
    except ObjectDoesNotExist:
        return None


def org_atual(request):
    perfil = perfil_do_usuario(request.user)
    return perfil.organizacao if perfil else None


def organizacao_requerida(view):
    """@login_required + garante que o usuário tem Perfil (logo, uma organização).

    Um superusuário sem Perfil daria RelatedObjectDoesNotExist em
    request.user.perfil. Em vez de quebrar, mostramos uma página explicando
    que ele precisa ser vinculado a uma organização pelo Admin.
    """

    @login_required
    @wraps(view)
    def _view(request, *args, **kwargs):
        if perfil_do_usuario(request.user) is None:
            return render(request, 'core/sem_organizacao.html', status=403)
        return view(request, *args, **kwargs)

    return _view
