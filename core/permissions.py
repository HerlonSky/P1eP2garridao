"""Permissões da API (DRF) ligadas à organização do usuário."""

from rest_framework.permissions import BasePermission

from .utils import perfil_do_usuario


class TemOrganizacao(BasePermission):
    """Só deixa passar usuários logados que tenham Perfil (e, portanto, organização)."""

    message = 'Usuário sem organização vinculada.'

    def has_permission(self, request, view):
        return perfil_do_usuario(request.user) is not None
