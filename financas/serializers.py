from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.utils import org_atual

from .models import Categoria, Conta, Lancamento, Orcamento, Parcela


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
            # Unicidade por organização (UniqueConstraint/unique_together com a org,
            # que não é um campo do serializer).
            instancia.validate_unique()
            instancia.validate_constraints()
        except DjangoValidationError as erro:
            if not hasattr(erro, 'error_dict'):
                raise serializers.ValidationError({'non_field_errors': erro.messages})
            erros = erro.message_dict
            if '__all__' in erros:
                erros['non_field_errors'] = erros.pop('__all__')
            raise serializers.ValidationError(erros)
        # o clean() pode normalizar campos (ex.: numero_parcelas = 1 se não parcelado)
        for campo in attrs:
            attrs[campo] = getattr(instancia, campo)
        return attrs


# Em todos os serializers os campos são listados um a um (nada de "__all__"),
# e "organizacao" fica de fora: quem define é o usuário logado.


class ContaSerializer(ValidaPeloModelMixin, serializers.ModelSerializer):
    saldo_atual = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Conta
        fields = ['id', 'nome', 'tipo', 'saldo_inicial', 'saldo_atual', 'criada_em']
        read_only_fields = ['criada_em']


class CategoriaSerializer(ValidaPeloModelMixin, serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nome', 'tipo']


class ParcelaResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parcela
        fields = ['id', 'numero', 'valor', 'data_vencimento', 'paga']


class LancamentoSerializer(DaOrganizacaoSerializerMixin, ValidaPeloModelMixin, serializers.ModelSerializer):
    campos_da_organizacao = {'conta': Conta, 'categoria': Categoria}

    # Relacionamentos: o id é usado para gravar; o nome vem junto só para leitura.
    conta_nome = serializers.CharField(source='conta.nome', read_only=True)
    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True)
    parcelas = ParcelaResumoSerializer(many=True, read_only=True)

    class Meta:
        model = Lancamento
        fields = [
            'id', 'conta', 'conta_nome', 'categoria', 'categoria_nome', 'descricao', 'valor',
            'tipo', 'data', 'parcelado', 'numero_parcelas', 'parcelas', 'criado_em',
        ]
        read_only_fields = ['criado_em']


class ParcelaSerializer(serializers.ModelSerializer):
    """Parcelas são geradas pelo lançamento: pela API só dá para marcar como paga."""

    lancamento_descricao = serializers.CharField(source='lancamento.descricao', read_only=True)

    class Meta:
        model = Parcela
        fields = ['id', 'lancamento', 'lancamento_descricao', 'numero', 'valor', 'data_vencimento', 'paga']
        read_only_fields = ['lancamento', 'numero', 'valor', 'data_vencimento']


class OrcamentoSerializer(DaOrganizacaoSerializerMixin, ValidaPeloModelMixin, serializers.ModelSerializer):
    campos_da_organizacao = {'categoria': Categoria}

    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True)
    valor_gasto = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    percentual_usado = serializers.FloatField(read_only=True)
    estourado = serializers.BooleanField(read_only=True)

    class Meta:
        model = Orcamento
        fields = [
            'id', 'categoria', 'categoria_nome', 'mes', 'ano', 'valor_limite',
            'valor_gasto', 'percentual_usado', 'estourado',
        ]
