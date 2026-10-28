from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from pedidos.models import ItemPedido, Pedido
from produtos.models import Produto

from .forms import CadastroForm


# "Mais vendidos" só aparece quando há vendas reais de pelo menos esta quantidade
# de produtos diferentes (pedidos cancelados não contam). Evita rotular como
# "mais vendido" algo que vendeu uma única vez num pedido de teste.
MIN_MAIS_VENDIDOS = 3


def home(request):
    ativos = Produto.objects.filter(ativo=True).prefetch_related("variantes")

    novidades = list(ativos.order_by("-criado_em", "-pk")[:4])

    # categorias visuais: a imagem de cada uma é a de um produto real dela
    categorias = []
    vistas = set()
    for produto in ativos.order_by("categoria", "nome"):
        chave = produto.categoria.lower()
        if chave in vistas:
            continue
        categorias.append({"nome": produto.categoria, "produto": produto})
        vistas.add(chave)
    # quantidade por categoria
    totais = {}
    for nome in ativos.values_list("categoria", flat=True):
        totais[nome.lower()] = totais.get(nome.lower(), 0) + 1
    for c in categorias:
        c["total"] = totais.get(c["nome"].lower(), 0)

    mais_vendidos = []
    ranking = (ItemPedido.objects
               .exclude(pedido__status=Pedido.Status.CANCELADO)
               .filter(produto__ativo=True)
               .values("produto")
               .annotate(vendidos=Sum("quantidade"))
               .order_by("-vendidos")[:4])
    ranking = list(ranking)
    if len(ranking) >= MIN_MAIS_VENDIDOS:
        por_id = {p.pk: p for p in ativos.filter(pk__in=[r["produto"] for r in ranking])}
        mais_vendidos = [por_id[r["produto"]] for r in ranking if r["produto"] in por_id]

    destaque = ativos.exclude(imagem="").order_by("-criado_em", "-pk").first()

    contexto = {
        "novidades": novidades,
        "categorias": categorias,
        "mais_vendidos": mais_vendidos,
        "destaque": destaque,
        # foto de capa opcional: basta salvar core/static/core/img/hero.jpg
        "tem_hero_foto": bool(finders.find("core/img/hero.jpg")),
        "total_produtos": ativos.count(),
    }

    return render(request, "core/home.html", contexto)


def sobre(request):
    return render(request, "core/sobre.html")

@login_required
def painel(request):
    # request.user é o usuário logado
    pedidos = (Pedido.objects
               .filter(usuario=request.user)
               .prefetch_related("itens")
               .order_by("-criado_em"))
    contexto = {
        "usuario": request.user,
        "total_pedidos": pedidos.count(),
        "pedidos_recentes": pedidos[:3],
    }
    return render(request, "core/painel.html", contexto)


def cadastro(request):
    # quem já está logado não precisa se cadastrar
    if request.user.is_authenticated:
        return redirect("home")

    form = CadastroForm(request.POST or None)
    if form.is_valid():
        usuario = form.save()          # cria um usuário comum (is_staff=False)
        login(request, usuario)        # já entra logado; o carrinho da sessão continua
        messages.success(request, "Conta criada com sucesso! Bem-vindo à OSStore.")

        # volta para onde a pessoa estava (ex.: carrinho), só se o destino for do próprio site
        destino = request.GET.get("next", "")
        if not url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
            destino = "home"
        return redirect(destino)

    return render(request, "registration/cadastro.html", {"form": form})
