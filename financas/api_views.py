from rest_framework import generics

from core.utils import org_atual

from .models import Lancamento
from .serializers import LancamentoSerializer


class DaOrganizacaoMixin:
    """Toda consulta da API parte da organização do usuário logado."""

    def get_queryset(self):
        return super().get_queryset().filter(organizacao=org_atual(self.request))

    def perform_create(self, serializer):
        # A organização vem do usuário, nunca do JSON enviado.
        serializer.save(organizacao=org_atual(self.request))


class LancamentoListCreate(DaOrganizacaoMixin, generics.ListCreateAPIView):
    """GET lista os lançamentos; POST cria um novo (e gera as parcelas)."""

    queryset = Lancamento.objects.select_related('conta', 'categoria')
    serializer_class = LancamentoSerializer


class LancamentoDetail(DaOrganizacaoMixin, generics.RetrieveUpdateDestroyAPIView):
    """GET detalha; PUT/PATCH atualiza; DELETE apaga. Id de outra organização dá 404."""

    queryset = Lancamento.objects.select_related('conta', 'categoria')
    serializer_class = LancamentoSerializer
