"""API REST do sistema (DRF).

ModelViewSet entrega as cinco operações do CRUD e o router gera as URLs.
Toda consulta parte da organização do usuário logado (DaOrganizacaoMixin), e as
permissões por papel seguem a mesma regra das telas:
- contas, categorias e orçamentos: todos leem, só administrador altera;
- lançamentos: operador cria e edita, só administrador exclui;
- parcelas: só leitura e PATCH do campo "paga".
"""

from django.db.models import ProtectedError, Q
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import EhAdminOuSomenteLeitura, SomenteAdminExclui, TemOrganizacao
from core.utils import org_atual

from .models import Categoria, Conta, Lancamento, Orcamento, Parcela
from .serializers import (
    CategoriaSerializer, ContaSerializer, LancamentoSerializer, OrcamentoSerializer, ParcelaSerializer,
)

PERMISSOES_BASE = [IsAuthenticated, TemOrganizacao]


class DaOrganizacaoMixin:
    """Toda consulta da API parte da organização do usuário logado.

    Um id de outra organização não entra no queryset, então dá 404.
    """

    campo_organizacao = 'organizacao'

    def get_queryset(self):
        return super().get_queryset().filter(**{self.campo_organizacao: org_atual(self.request)})

    def perform_create(self, serializer):
        # A organização vem do usuário, nunca do JSON enviado.
        serializer.save(organizacao=org_atual(self.request))

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': 'Registro em uso por lançamentos ou orçamentos; não pode ser excluído.'},
                status=status.HTTP_409_CONFLICT,
            )


class ContaViewSet(DaOrganizacaoMixin, viewsets.ModelViewSet):
    queryset = Conta.objects.all()
    serializer_class = ContaSerializer
    permission_classes = PERMISSOES_BASE + [EhAdminOuSomenteLeitura]


class CategoriaViewSet(DaOrganizacaoMixin, viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = PERMISSOES_BASE + [EhAdminOuSomenteLeitura]


class LancamentoViewSet(DaOrganizacaoMixin, viewsets.ModelViewSet):
    """Aceita os mesmos filtros da tela: ?q=<descrição>&categoria=<id>."""

    queryset = Lancamento.objects.select_related('conta', 'categoria').prefetch_related('parcelas')
    serializer_class = LancamentoSerializer
    permission_classes = PERMISSOES_BASE + [SomenteAdminExclui]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get('q', '').strip()
        categoria = self.request.query_params.get('categoria', '')
        filtros = Q()
        if q:
            filtros &= Q(descricao__icontains=q)
        if categoria.isdigit():
            filtros &= Q(categoria_id=categoria)
        return qs.filter(filtros)


class ParcelaViewSet(DaOrganizacaoMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Parcelas são criadas pelo lançamento; aqui só lista, detalha e marca como paga."""

    campo_organizacao = 'lancamento__organizacao'
    queryset = Parcela.objects.select_related('lancamento')
    serializer_class = ParcelaSerializer
    permission_classes = PERMISSOES_BASE
    http_method_names = ['get', 'patch', 'head', 'options']


class OrcamentoViewSet(DaOrganizacaoMixin, viewsets.ModelViewSet):
    queryset = Orcamento.objects.select_related('categoria')
    serializer_class = OrcamentoSerializer
    permission_classes = PERMISSOES_BASE + [EhAdminOuSomenteLeitura]
