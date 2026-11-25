from django import forms

from .models import Categoria, Conta, Lancamento, Orcamento


class FormDaOrganizacao(forms.ModelForm):
    """Base dos forms de negócio: recebe a organização do usuário logado.

    - O campo "organizacao" NUNCA aparece no form (o usuário poderia escolher
      a organização que quisesse); a view preenche com commit=False.
    - Todo select de FK é filtrado pela organização, senão as opções de outras
      organizações vazariam na tela.
    """

    # nome do campo -> model, para filtrar o queryset do select
    campos_da_organizacao = {}

    def __init__(self, *args, org=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.org = org
        # Preenche a organização já na validação, para o clean() do model
        # conseguir conferir que conta/categoria são da mesma organização.
        if org is not None and self.instance.organizacao_id is None:
            self.instance.organizacao = org
        for campo, model in self.campos_da_organizacao.items():
            self.fields[campo].queryset = model.objects.filter(organizacao=org)


class LancamentoForm(FormDaOrganizacao):
    campos_da_organizacao = {'conta': Conta, 'categoria': Categoria}

    class Meta:
        model = Lancamento
        fields = ['conta', 'categoria', 'descricao', 'valor', 'tipo', 'data', 'parcelado', 'numero_parcelas']
        widgets = {
            'conta': forms.Select(attrs={'class': 'form-select'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'parcelado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'numero_parcelas': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }
    # A validação (valor > 0 e número de parcelas) fica em Lancamento.clean():
    # o ModelForm chama o clean() do model automaticamente.


class OrcamentoForm(FormDaOrganizacao):
    campos_da_organizacao = {'categoria': Categoria}

    class Meta:
        model = Orcamento
        fields = ['categoria', 'mes', 'ano', 'valor_limite']
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'mes': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '12'}),
            'ano': forms.NumberInput(attrs={'class': 'form-control'}),
            'valor_limite': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
        }
