from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from produtos.models import Produto, Variante

from . import carrinho as cart
from .models import ItemPedido, Pedido
from .servicos import cancelar_pedido


def _inteiro(valor, padrao=0):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


def _nome_item(produto, variante):
    return f"{produto.nome} ({variante.rotulo})" if variante else produto.nome


# ---------------------------------------------------------------- carrinho

def ver_carrinho(request):
    dados = cart.detalhar(request)

    # tira da sessão o que não está mais à venda e avisa a pessoa
    if dados["removidos"]:
        validos = {(i["produto"].pk, i["variante_id"]): i["quantidade"] for i in dados["itens"]}
        cart.salvar(request, validos)
        messages.warning(
            request,
            "Alguns itens deixaram de estar disponíveis e foram removidos do carrinho.",
        )

    return render(request, "pedidos/carrinho.html", dados)


@require_POST
def adicionar(request, pk):
    produto = get_object_or_404(
        Produto.objects.prefetch_related("variantes"), pk=pk, ativo=True)

    variante = None
    if produto.tem_variantes:
        vid = _inteiro(request.POST.get("variante"))
        variante = next((v for v in produto.variantes_ativas() if v.pk == vid), None)
        if variante is None:
            messages.error(request, "Escolha uma opção (tamanho/cor) antes de adicionar ao carrinho.")
            return redirect("produto_detalhe", pk=produto.pk)
        disponivel = variante.estoque
    else:
        disponivel = produto.estoque

    quantidade = max(1, min(_inteiro(request.POST.get("quantidade"), 1), cart.MAX_POR_ITEM))
    carrinho = cart.ler(request)
    chave = (produto.pk, variante.pk if variante else 0)
    atual = carrinho.get(chave, 0)
    nome = _nome_item(produto, variante)

    if disponivel <= atual:
        if disponivel == 0:
            messages.error(request, f"“{nome}” está esgotado.")
        else:
            messages.warning(
                request,
                f"Você já tem todas as {disponivel} unidades de “{nome}” no carrinho.",
            )
        return redirect("ver_carrinho")

    if atual + quantidade > disponivel:
        quantidade = disponivel - atual
        messages.warning(request, f"Só temos {disponivel} unidade(s) de “{nome}”; ajustamos a quantidade.")

    carrinho[chave] = atual + quantidade
    cart.salvar(request, carrinho)                             # salva de volta na sessão
    messages.success(request, f"“{nome}” foi adicionado ao carrinho.")
    return redirect("ver_carrinho")


@require_POST
def alterar(request, pk):
    """Botões do carrinho: acao = mais | menos | remover (variante vem no POST)."""
    produto = get_object_or_404(Produto, pk=pk)
    vid = _inteiro(request.POST.get("variante"))
    variante = None
    if vid:
        variante = get_object_or_404(Variante, pk=vid, produto=produto)

    carrinho = cart.ler(request)
    chave = (produto.pk, vid)
    acao = request.POST.get("acao")
    atual = carrinho.get(chave, 0)
    estoque = variante.estoque if variante else produto.estoque
    nome = _nome_item(produto, variante)

    if acao == "remover":
        carrinho.pop(chave, None)
        messages.info(request, f"“{nome}” foi removido do carrinho.")
    elif acao == "mais" and atual:
        if atual >= estoque:
            messages.warning(request, f"Só temos {estoque} unidade(s) de “{nome}”.")
        else:
            carrinho[chave] = atual + 1
    elif acao == "menos" and atual:
        if atual <= 1:
            carrinho.pop(chave, None)
            messages.info(request, f"“{nome}” foi removido do carrinho.")
        else:
            carrinho[chave] = atual - 1

    cart.salvar(request, carrinho)
    return redirect("ver_carrinho")


# ----------------------------------------------------------------- pedidos

@login_required
def finalizar(request):
    # criar pedido muda dados: só acontece por POST (botão do carrinho), nunca por um link
    if request.method != "POST":
        return redirect("ver_carrinho")

    carrinho = cart.ler(request)
    if not carrinho:
        messages.info(request, "Seu carrinho está vazio.")
        return redirect("produtos")

    with transaction.atomic():                 # tudo ou nada
        # trava as linhas para checar e baixar o estoque com segurança
        # (efetivo em PostgreSQL/MySQL; o SQLite serializa as escritas sozinho)
        produtos = Produto.objects.select_for_update().filter(
            pk__in={pk for pk, _ in carrinho}, ativo=True)
        por_id = {p.pk: p for p in produtos}
        variantes = Variante.objects.select_for_update().filter(
            pk__in={vid for _, vid in carrinho if vid}, ativo=True)
        variante_por_id = {v.pk: v for v in variantes}
        # produtos que passaram a ter variantes depois de entrarem no carrinho
        com_variantes = set(
            Variante.objects.filter(produto_id__in=por_id.keys(), ativo=True)
            .values_list("produto_id", flat=True))

        problemas = []
        itens_validos = []
        for (pk, vid), qtd in carrinho.items():
            produto = por_id.get(pk)
            variante = variante_por_id.get(vid) if vid else None
            if produto is None or (vid and (variante is None or variante.produto_id != pk)):
                problemas.append("Um dos itens do carrinho não está mais disponível.")
                continue
            if not vid and pk in com_variantes:
                problemas.append(f"“{produto.nome}”: escolha o tamanho/cor novamente.")
                continue
            estoque = variante.estoque if variante else produto.estoque
            if qtd > estoque:
                problemas.append(f"“{_nome_item(produto, variante)}”: restam apenas {estoque} em estoque.")
                continue
            itens_validos.append((produto, variante, qtd))

        if problemas:
            for texto in dict.fromkeys(problemas):      # sem repetir mensagens
                messages.error(request, texto)
            return redirect("ver_carrinho")

        pedido = Pedido.objects.create(usuario=request.user)
        for produto, variante, qtd in itens_validos:
            ItemPedido.objects.create(
                pedido=pedido, produto=produto, variante=variante,
                descricao_variante=variante.rotulo if variante else "",
                quantidade=qtd, preco=produto.preco,      # preço sempre do banco
            )
            alvo = variante if variante else produto
            alvo.estoque -= qtd
            alvo.save(update_fields=["estoque"])

    cart.salvar(request, {})                   # esvazia o carrinho
    messages.success(
        request,
        f"Pedido #{pedido.pk} registrado. Ele está pendente: o pagamento ainda não foi confirmado.",
    )
    return redirect("pedido_detalhe", pk=pedido.pk)


@login_required
def meus_pedidos(request):
    # prefetch_related evita uma consulta por pedido (mais rápido)
    pedidos = (Pedido.objects
               .filter(usuario=request.user)
               .prefetch_related("itens")
               .order_by("-criado_em"))
    return render(request, "pedidos/meus.html", {"pedidos": pedidos})


@login_required
def detalhe(request, pk):
    # o filtro usuario=request.user impede ver pedido de outra pessoa
    pedido = get_object_or_404(
        Pedido.objects.prefetch_related("itens__produto"),
        pk=pk, usuario=request.user,
    )
    return render(request, "pedidos/detalhe.html", {"pedido": pedido})


@login_required
@require_POST
def cancelar(request, pk):
    # só o dono do pedido; só enquanto pendente; devolve o estoque
    pedido = get_object_or_404(Pedido, pk=pk, usuario=request.user)
    if cancelar_pedido(pedido.pk, usuario=request.user):
        messages.success(request, f"Pedido #{pedido.pk} cancelado.")
    else:
        messages.error(request, "Este pedido não pode mais ser cancelado.")
    return redirect("pedido_detalhe", pk=pedido.pk)
