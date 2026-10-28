def carrinho(request):
    """Disponibiliza `carrinho_qtd` em todos os templates (usado na navbar)."""
    sessao = getattr(request, "session", None)
    bruto = sessao.get("carrinho", {}) if sessao is not None else {}
    try:
        qtd = sum(int(q) for q in bruto.values())
    except (AttributeError, TypeError, ValueError):
        qtd = 0
    return {"carrinho_qtd": qtd}
