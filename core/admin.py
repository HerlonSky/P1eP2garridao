from django.contrib import admin

from .models import Organizacao, Perfil


class PerfilInline(admin.TabularInline):
    model = Perfil
    extra = 0


@admin.register(Organizacao)
class OrganizacaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'criada_em')
    search_fields = ('nome',)
    inlines = [PerfilInline]


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'organizacao')
    list_filter = ('organizacao',)
    search_fields = ('usuario__username',)
