from rest_framework import serializers

from .models import Lancamento


class LancamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lancamento
        # Campos listados um a um (nada de "__all__"), como pede a Aula 13.
        fields = [
            'id', 'conta', 'categoria', 'descricao', 'valor', 'tipo',
            'data', 'parcelado', 'numero_parcelas', 'criado_em',
        ]
        read_only_fields = ['criado_em']
