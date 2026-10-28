from django.urls import path
from . import views

urlpatterns = [
    path("produtos/", views.lista_produtos, name="produtos"),
    path("produtos/novo/", views.produto_novo, name="produto_novo"),
    path("produtos/<int:pk>/", views.produto_detalhe, name="produto_detalhe"),
    path("produtos/<int:pk>/editar/", views.produto_editar, name="produto_editar"),
]
