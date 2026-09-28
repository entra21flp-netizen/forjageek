from django.urls import path

from . import views

app_name = "dioramas_novo"
urlpatterns = [
    path("novo/", views.selecionar_colecionavel, name="selecionar"),
    path("novo/<int:colecionavel_id>/", views.configurar, name="configurar"),
    path("novo/<int:colecionavel_id>/gerar/", views.gerar, name="gerar"),
    path("preview/", views.preview, name="preview"),
    path("confirmar/", views.confirmar, name="confirmar"),
    path("cancelar/", views.cancelar, name="cancelar"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/posicionar/", views.posicionar, name="posicionar"),
    path("<int:pk>/remover-da-prateleira/", views.remover_prateleira, name="remover_prateleira"),
    path("<int:pk>/excluir/", views.excluir, name="excluir"),
]
