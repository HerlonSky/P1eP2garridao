from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.utils import org_atual

from .models import Categoria, Conta, Lancamento


class DaOrganizacaoSerializerMixin:
    """Filtra os campos de FK pela organização do usuário logado.

    É o equivalente, na API, ao select filtrado do formulário: um id de conta
    ou categoria de outra organização vira erro 400 ("objeto não existe").
    """

    campos_da_organizacao = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        org = org_atual(request) if request else None
        for campo, model in self.campos_da_organizacao.items():
            if campo in self.fields:
                self.fields[campo].queryset = model.objects.filter(organizacao=org)


class ValidaPeloModelMixin:
    """Reaproveita o clean() do model no serializer.

    Assim a regra de negócio tem um lugar só (o model) e vale igual nas
    telas, no Admin e na API. O erro do Django vira resposta 400 em JSON.
    """

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instancia = self.instance or self.Meta.model()
        request = self.context.get('request')
        if instancia.organizacao_id is None and request is not None:
            instancia.organizacao = org_atual(request)
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        try:
            instancia.clean()
        except DjangoValidationError as erro:
            raise serializers.ValidationError(
                erro.message_dict if hasattr(erro, 'error_dict') else {'non_field_errors': erro.messages}
            )
        # o clean() pode normalizar campos (ex.: numero_parcelas = 1 se não parcelado)
        for campo in attrs:
            attrs[campo] = getattr(instancia, campo)
        return attrs


class LancamentoSerializer(DaOrganizacaoSerializerMixin, ValidaPeloModelMixin, serializers.ModelSerializer):
    campos_da_organizacao = {'conta': Conta, 'categoria': Categoria}

    class Meta:
        model = Lancamento
        # Campos listados um a um (nada de "__all__"), como pede a Aula 13.
        # "organizacao" fica fora: quem define é o usuário logado.
        fields = [
            'id', 'conta', 'categoria', 'descricao', 'valor', 'tipo',
            'data', 'parcelado', 'numero_parcelas', 'criado_em',
        ]
        read_only_fields = ['criado_em']
