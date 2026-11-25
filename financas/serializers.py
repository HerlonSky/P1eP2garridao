from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Lancamento


class ValidaPeloModelMixin:
    """Reaproveita o clean() do model no serializer.

    Assim a regra de negócio tem um lugar só (o model) e vale igual nas
    telas, no Admin e na API. O erro do Django vira resposta 400 em JSON.
    """

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instancia = self.instance or self.Meta.model()
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


class LancamentoSerializer(ValidaPeloModelMixin, serializers.ModelSerializer):
    class Meta:
        model = Lancamento
        # Campos listados um a um (nada de "__all__"), como pede a Aula 13.
        fields = [
            'id', 'conta', 'categoria', 'descricao', 'valor', 'tipo',
            'data', 'parcelado', 'numero_parcelas', 'criado_em',
        ]
        read_only_fields = ['criado_em']
