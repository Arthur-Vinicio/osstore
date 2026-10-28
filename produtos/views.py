from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProdutoForm
from .models import Produto

POR_PAGINA = 12

ORDENACOES = {
    "nome": ("Nome (A–Z)", ("nome", "pk")),
    "preco_asc": ("Menor preço", ("preco", "nome")),
    "preco_desc": ("Maior preço", ("-preco", "nome")),
    "novos": ("Mais recentes", ("-criado_em", "-pk")),
}


def _preco(valor):
    """Lê um preço digitado na URL (aceita vírgula). Devolve None se inválido."""
    try:
        numero = Decimal((valor or "").strip().replace(",", "."))
    except InvalidOperation:
        return None
    if not numero.is_finite() or numero < 0 or numero >= Decimal("100000000"):
        return None
    return numero


def lista_produtos(request):
    # só produtos ativos
    produtos = Produto.objects.filter(ativo=True).prefetch_related("variantes")

    # busca opcional pela caixa de pesquisa (?q=...)
    termo = (request.GET.get("q") or "").strip()
    if termo:
        produtos = produtos.filter(
            Q(nome__icontains=termo) | Q(categoria__icontains=termo)
            | Q(descricao__icontains=termo))

    categoria = (request.GET.get("categoria") or "").strip()
    if categoria:
        produtos = produtos.filter(categoria__iexact=categoria)

    preco_min = _preco(request.GET.get("preco_min"))
    preco_max = _preco(request.GET.get("preco_max"))
    if preco_min is not None:
        produtos = produtos.filter(preco__gte=preco_min)
    if preco_max is not None:
        produtos = produtos.filter(preco__lte=preco_max)

    ordem = request.GET.get("ordem")
    if ordem not in ORDENACOES:
        ordem = "nome"
    produtos = produtos.order_by(*ORDENACOES[ordem][1])

    pagina = Paginator(produtos, POR_PAGINA).get_page(request.GET.get("page"))

    # querystring sem "page", para os links da paginação manterem os filtros
    params = request.GET.copy()
    params.pop("page", None)

    categorias = (Produto.objects.filter(ativo=True)
                  .values("categoria").annotate(total=Count("pk")).order_by("categoria"))

    filtros_ativos = bool(termo or categoria or preco_min is not None or preco_max is not None)

    return render(request, "produtos/lista.html", {
        "pagina": pagina,
        "produtos": pagina.object_list,
        "total": pagina.paginator.count,
        "categorias": categorias,
        "ordenacoes": [(k, v[0]) for k, v in ORDENACOES.items()],
        "q": termo,
        "categoria_atual": categoria,
        "preco_min": request.GET.get("preco_min", "") if preco_min is not None else "",
        "preco_max": request.GET.get("preco_max", "") if preco_max is not None else "",
        "ordem": ordem,
        "filtros_ativos": filtros_ativos,
        "querystring": params.urlencode(),
    })


def produto_detalhe(request, pk):
    produto = get_object_or_404(
        Produto.objects.prefetch_related("variantes", "imagens"), pk=pk, ativo=True)

    # relacionados: mesma categoria primeiro; se faltar, completa com os mais novos
    relacionados = list(
        Produto.objects.filter(ativo=True, categoria__iexact=produto.categoria)
        .exclude(pk=produto.pk).prefetch_related("variantes").order_by("-criado_em")[:4])
    if len(relacionados) < 4:
        ja = [produto.pk] + [r.pk for r in relacionados]
        relacionados += list(
            Produto.objects.filter(ativo=True).exclude(pk__in=ja)
            .prefetch_related("variantes").order_by("-criado_em")[: 4 - len(relacionados)])

    imagens = []
    if produto.imagem:
        imagens.append({"url": produto.imagem.url, "legenda": produto.nome})
    for extra in produto.imagens.all():
        imagens.append({"url": extra.imagem.url, "legenda": extra.legenda or produto.nome})

    return render(request, "produtos/detalhe.html", {
        "produto": produto,
        "variantes": produto.variantes_ativas(),
        "imagens": imagens,
        "relacionados": relacionados,
    })


def eh_equipe(user):
    return user.is_staff


@login_required
@user_passes_test(eh_equipe)
def produto_novo(request):
    if request.method == "POST":
        form = ProdutoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("produtos")
    else:
        form = ProdutoForm()
    return render(request, "produtos/form.html", {"form": form})


@login_required
@user_passes_test(eh_equipe)
def produto_editar(request, pk):
    produto = get_object_or_404(Produto, pk=pk)

    form = ProdutoForm(
        request.POST or None,
        request.FILES or None,
        instance=produto
    )

    if form.is_valid():
        form.save()
        return redirect("produtos")

    return render(
        request,
        "produtos/form.html",
        {"form": form}
    )
