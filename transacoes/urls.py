from django.urls import path
from . import views

app_name = "transacoes"
urlpatterns = [
    path("vendas/", views.historico_vendas, name="historico_vendas"),
    path("vendas/<int:venda_id>/avaliar/", views.avaliar_venda, name="avaliar_venda"),
    path("checkout/", views.iniciar_checkout_carrinho, name="iniciar_checkout_carrinho"),
    path("checkout/sucesso/", views.checkout_sucesso, name="checkout_sucesso"),
    path("checkout/cancelado/", views.checkout_cancelado, name="checkout_cancelado"),
    path("stripe/webhook/", views.webhook_stripe, name="webhook_stripe"),
]
