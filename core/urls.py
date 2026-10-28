from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("sobre/", views.sobre, name="sobre"),
    path("painel/", views.painel, name="painel"),
    path("cadastro/", views.cadastro, name="cadastro"),
]