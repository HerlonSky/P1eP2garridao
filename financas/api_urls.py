from rest_framework.routers import DefaultRouter

from . import api_views

# O router gera, para cada recurso, /api/<recurso>/ e /api/<recurso>/<id>/,
# além da raiz navegável /api/.
router = DefaultRouter()
router.register('contas', api_views.ContaViewSet, basename='api-conta')
router.register('categorias', api_views.CategoriaViewSet, basename='api-categoria')
router.register('lancamentos', api_views.LancamentoViewSet, basename='api-lancamento')
router.register('parcelas', api_views.ParcelaViewSet, basename='api-parcela')
router.register('orcamentos', api_views.OrcamentoViewSet, basename='api-orcamento')

urlpatterns = router.urls
