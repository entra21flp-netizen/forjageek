from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from usuarios import views as usuario_views

app_name = "core"

urlpatterns = [
    path("catalogo/action-figures/", views.catalogo_figuras, name="catalogo_figuras"),
    path("colecionaveis/cadastrar/", views.cadastrar_colecionavel, name="cadastrar_colecionavel"),
    path("colecionaveis/<int:item_id>/editar/", views.editar_colecionavel, name="editar_colecionavel"),
    path("colecionaveis/analisar-foto/", views.analisar_foto_cadastro, name="analisar_foto_cadastro"),
    path("", views.index, name="index"),
    path("produto/<int:item_id>/", views.produto, name="produto"),
    path("carrinho/adicionar/", views.adicionar_ao_carrinho, name="adicionar_ao_carrinho"),
    path("carrinho/remover/", views.remover_do_carrinho, name="remover_do_carrinho"),
    path("prateleira/", views.prateleira, name="prateleira"),
    path("colecionaveis/", views.meus_colecionaveis, name="meus_colecionaveis"),
    path("prateleira/mover-item/", views.mover_item_estante, name="mover_item_estante"),
    path("prateleira/adicionar-item/", views.adicionar_item_estante, name="adicionar_item_estante"),
    path("prateleira/remover-item/", views.remover_item_estante, name="remover_item_estante"),
    path("prateleira/salvar-dioramas/", views.salvar_dioramas, name="salvar_dioramas"),
    path("prateleira/selecionar-diorama/", views.selecionar_diorama_destaque, name="selecionar_diorama_destaque"),
    path("prateleira/criar-estante/", views.criar_estante, name="criar_estante"),
    path("prateleira/alterar-privacidade/", views.alterar_privacidade_estante, name="alterar_privacidade_estante"),
    path("colecionador/<str:username>/", views.prateleira_publica, name="prateleira_publica"),
    path("prateleira/<int:estante_id>/avaliar/", views.avaliar_estante, name="avaliar_estante"),
    path("ranking-estantes/", views.ranking_estantes, name="ranking_estantes"),
    path("colecionadores/", views.buscar_colecionadores, name="buscar_colecionadores"),
    path("perfil/<str:username>/", views.perfil_colecionador, name="perfil_colecionador"),
    path("wishlist/", views.wishlist, name="wishlist"),
    path("wishlist/alternar/", views.alternar_wishlist, name="alternar_wishlist"),
    path("chat/", views.chat, name="chat"),
    path("chat/<int:conversa_id>/", views.chat, name="chat_conversa"),
    path("chat/iniciar/<int:item_id>/", views.iniciar_chat, name="iniciar_chat"),
    path("chat/<int:conversa_id>/enviar/", views.enviar_mensagem, name="enviar_mensagem"),
    path(
        "entrar/",
        auth_views.LoginView.as_view(template_name="core/login.html"),
        name="login",
    ),
    path("criar-conta/", usuario_views.cadastrar_usuario, name="cadastro_usuario"),
    path("recuperar-conta/", usuario_views.recuperar_conta, name="recuperar_conta"),
    path("recuperar-conta/<uidb64>/<token>/", usuario_views.redefinir_senha_email, name="redefinir_senha_email"),
    path("verificar-whatsapp/", usuario_views.verificar_whatsapp, name="verificar_whatsapp"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
]
