"""Permissões da API (DRF) ligadas à organização do usuário."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .utils import perfil_do_usuario


class TemOrganizacao(BasePermission):
    """Só deixa passar usuários logados que tenham Perfil (e, portanto, organização)."""

    message = 'Usuário sem organização vinculada.'

    def has_permission(self, request, view):
        return perfil_do_usuario(request.user) is not None


def _eh_admin(request):
    perfil = perfil_do_usuario(request.user)
    return perfil is not None and perfil.eh_admin


class EhAdminOuSomenteLeitura(BasePermission):
    """Todos da organização leem (GET); só administradores criam, alteram e apagam."""

    message = 'Apenas administradores podem alterar este recurso.'

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or _eh_admin(request)


class SomenteAdminExclui(BasePermission):
    """Operador pode criar e editar, mas só administrador apaga (DELETE)."""

    message = 'Apenas administradores podem excluir.'

    def has_permission(self, request, view):
        return request.method != 'DELETE' or _eh_admin(request)


class EhAdmin(BasePermission):
    """Endpoint exclusivo de administradores."""

    message = 'Apenas administradores.'

    def has_permission(self, request, view):
        return _eh_admin(request)
