from django.conf import settings


def modo_demo(request):
    """Em desenvolvimento (DEBUG=True), a tela de login mostra os usuários de demonstração."""
    return {'modo_demo': settings.DEBUG}
