from django.contrib import admin

from .models import Categoria, Conta, Lancamento, Orcamento, Parcela


class ParcelaInline(admin.TabularInline):
    model = Parcela
    extra = 0
    can_delete = False
    fields = ('numero', 'valor', 'data_vencimento', 'paga')
    readonly_fields = ('numero', 'valor', 'data_vencimento')


@admin.register(Conta)
class ContaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'organizacao', 'tipo', 'saldo_inicial', 'saldo_atual')
    list_select_related = ('organizacao',)

    def get_queryset(self, request):
        return super().get_queryset(request).com_saldo()
    list_filter = ('organizacao', 'tipo')
    search_fields = ('nome',)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'organizacao', 'tipo')
    list_filter = ('organizacao', 'tipo')
    search_fields = ('nome',)


@admin.register(Lancamento)
class LancamentoAdmin(admin.ModelAdmin):
    # A validação do valor (> 0) está em Lancamento.clean(), que o Admin já chama.
    list_display = ('descricao', 'organizacao', 'conta', 'categoria', 'tipo', 'valor', 'data', 'parcelado', 'numero_parcelas')
    list_filter = ('organizacao', 'tipo', 'parcelado')
    search_fields = ('descricao',)
    date_hierarchy = 'data'
    inlines = [ParcelaInline]


@admin.register(Orcamento)
class OrcamentoAdmin(admin.ModelAdmin):
    list_display = ('categoria', 'organizacao', 'mes', 'ano', 'valor_limite', 'valor_gasto', 'percentual_usado', 'estourado')
    list_filter = ('organizacao', 'ano', 'mes')
    list_select_related = ('categoria', 'organizacao')

    def get_queryset(self, request):
        return super().get_queryset(request).com_gasto()


@admin.register(Parcela)
class ParcelaAdmin(admin.ModelAdmin):
    list_display = ('lancamento', 'numero', 'valor', 'data_vencimento', 'paga')
    list_filter = ('lancamento__organizacao', 'paga', 'data_vencimento')
    search_fields = ('lancamento__descricao',)
