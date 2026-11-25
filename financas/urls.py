from django.urls import path

from . import views, views_cadastros as cad

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard),  # mesmo dashboard, no endereço usado na Aula 17
    path('dashboard/exportar.csv', views.dashboard_exportar_csv, name='dashboard_exportar_csv'),

    path('lancamentos/', views.lancamento_lista, name='lancamento_lista'),
    path('lancamentos/novo/', views.lancamento_criar, name='lancamento_criar'),
    path('lancamentos/<int:pk>/editar/', cad.lancamento_editar, name='lancamento_editar'),
    path('lancamentos/<int:pk>/excluir/', cad.lancamento_excluir, name='lancamento_excluir'),

    path('orcamentos/', views.orcamento_lista, name='orcamento_lista'),
    path('orcamentos/novo/', views.orcamento_criar, name='orcamento_criar'),
    path('orcamentos/<int:pk>/editar/', cad.orcamento_editar, name='orcamento_editar'),
    path('orcamentos/<int:pk>/excluir/', cad.orcamento_excluir, name='orcamento_excluir'),

    path('parcelas/', views.parcela_lista, name='parcela_lista'),
    path('parcelas/<int:pk>/marcar-paga/', views.parcela_marcar_paga, name='parcela_marcar_paga'),

    path('contas/', cad.conta_lista, name='conta_lista'),
    path('contas/nova/', cad.conta_criar, name='conta_criar'),
    path('contas/<int:pk>/editar/', cad.conta_editar, name='conta_editar'),
    path('contas/<int:pk>/excluir/', cad.conta_excluir, name='conta_excluir'),

    path('categorias/', cad.categoria_lista, name='categoria_lista'),
    path('categorias/nova/', cad.categoria_criar, name='categoria_criar'),
    path('categorias/<int:pk>/editar/', cad.categoria_editar, name='categoria_editar'),
    path('categorias/<int:pk>/excluir/', cad.categoria_excluir, name='categoria_excluir'),
]
