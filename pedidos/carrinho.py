"""Funções de apoio para o carrinho de compras (guardado na sessão).

A sessão guarda um dicionário {"<id do produto>:<id da variante>": quantidade}.
Produto sem variantes usa variante 0 (ex.: "4:0"). Carrinhos antigos, cuja chave
era só o id do produto ("4"), continuam funcionando e são lidos como "4:0".

Nada vindo do navegador é usado como preço: preço e estoque sempre vêm do banco.
"""
from decimal import Decimal

from produtos.models import Produto, Variante

MAX_POR_ITEM = 99


def _chave(texto):
    """Converte a chave da sessão em (produto_id, variante_id) ou None se inválida."""
    partes = str(texto).split(":", 1)
    try:
        produto_id = int(partes[0])
        variante_id = int(partes[1]) if len(partes) == 2 else 0
    except (TypeError, ValueError):
        return None
    if produto_id <= 0 or variante_id < 0:
        return None
    return produto_id, variante_id


def ler(request):
    """Devolve o carrinho da sessão saneado: {(produto_id, variante_id): quantidade}."""
    bruto = request.session.get("carrinho", {})
    limpo = {}
    if not isinstance(bruto, dict):
        return limpo
    for chave, qtd in bruto.items():
        par = _chave(chave)
        try:
            qtd = int(qtd)
        except (TypeError, ValueError):
            continue
        if par is None or qtd <= 0:
            continue
        limpo[par] = limpo.get(par, 0) + min(qtd, MAX_POR_ITEM)
    return limpo


def salvar(request, carrinho):
    """Grava o carrinho de volta na sessão (chaves viram texto, como a sessão exige)."""
    request.session["carrinho"] = {
        f"{pk}:{vid}": qtd for (pk, vid), qtd in carrinho.items()
    }


def detalhar(request):
    """Monta os itens do carrinho com produto, variante, subtotal e total.

    Itens cujo produto/variante foi desativado ou apagado, ou que exigem uma
    variante que não foi escolhida, são ignorados e contados em `removidos`.
    """
    carrinho = ler(request)
    produtos = (Produto.objects
                .filter(pk__in={pk for pk, _ in carrinho}, ativo=True)
                .prefetch_related("variantes"))
    por_id = {p.pk: p for p in produtos}
    variantes = Variante.objects.filter(
        pk__in={vid for _, vid in carrinho if vid}, ativo=True)
    variante_por_id = {v.pk: v for v in variantes}

    itens = []
    total = Decimal("0")
    for (pk, vid), qtd in carrinho.items():
        produto = por_id.get(pk)
        if produto is None:
            continue
        variante = None
        if vid:
            variante = variante_por_id.get(vid)
            if variante is None or variante.produto_id != pk:
                continue
        elif produto.tem_variantes:
            continue                      # produto exige escolha de variante
        estoque = variante.estoque if variante else produto.estoque
        subtotal = produto.preco * qtd
        total += subtotal
        itens.append({
            "produto": produto,
            "variante": variante,
            "variante_id": vid,
            "estoque": estoque,
            "quantidade": qtd,
            "subtotal": subtotal,
            "sem_estoque": qtd > estoque,   # pediu mais do que existe
        })

    return {
        "itens": itens,
        "total": total,
        "quantidade_total": sum(i["quantidade"] for i in itens),
        "removidos": len(carrinho) - len(itens),
        "tem_problema": any(i["sem_estoque"] for i in itens),
    }
