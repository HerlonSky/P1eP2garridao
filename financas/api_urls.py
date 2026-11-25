from django.urls import path

from .api_views import LancamentoDetail, LancamentoListCreate

urlpatterns = [
    path('lancamentos/', LancamentoListCreate.as_view(), name='api_lancamento_lista'),
    path('lancamentos/<int:pk>/', LancamentoDetail.as_view(), name='api_lancamento_detalhe'),
]
