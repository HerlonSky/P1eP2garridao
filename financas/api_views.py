from rest_framework import generics

from .models import Lancamento
from .serializers import LancamentoSerializer


class LancamentoListCreate(generics.ListCreateAPIView):
    """GET lista os lançamentos; POST cria um novo (e gera as parcelas)."""

    queryset = Lancamento.objects.select_related('conta', 'categoria')
    serializer_class = LancamentoSerializer


class LancamentoDetail(generics.RetrieveUpdateDestroyAPIView):
    """GET detalha; PUT/PATCH atualiza; DELETE apaga."""

    queryset = Lancamento.objects.select_related('conta', 'categoria')
    serializer_class = LancamentoSerializer
