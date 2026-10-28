from django.urls import path

from . import views

urlpatterns = [
    # carrinho
    path("carrinho/", views.ver_carrinho, name="ver_carrinho"),
    path("carrinho/adicionar/<int:pk>/", views.adicionar, name="adicionar"),
    path("carrinho/alterar/<int:pk>/", views.alterar, name="alterar_carrinho"),
    path("finalizar/", views.finalizar, name="finalizar"),

    # pedidos do cliente
    path("pedidos/", views.meus_pedidos, name="meus_pedidos"),
    path("pedidos/<int:pk>/", views.detalhe, name="pedido_detalhe"),
    path("pedidos/<int:pk>/cancelar/", views.cancelar, name="pedido_cancelar"),
]
