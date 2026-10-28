"""Regras de negócio dos pedidos que mexem em estoque."""
from django.db import transaction
from django.db.models import F

from produtos.models import Produto, Variante

from .models import Pedido


@transaction.atomic
def cancelar_pedido(pedido_id, usuario=None):
    """Cancela um pedido PENDENTE e devolve os itens ao estoque.

    Retorna True se cancelou; False se o pedido não existe (ou não é do
    `usuario`, quando informado) ou se já não estava pendente.

    A linha do pedido é travada e o status é relido já dentro da transação:
    dois cancelamentos simultâneos não devolvem o estoque duas vezes.
    """
    consulta = Pedido.objects.select_for_update().filter(pk=pedido_id)
    if usuario is not None:
        consulta = consulta.filter(usuario=usuario)
    pedido = consulta.first()
    if pedido is None or pedido.status != Pedido.Status.NOVO:
        return False

    for item in pedido.itens.all():
        if item.variante_id:
            Variante.objects.filter(pk=item.variante_id).update(
                estoque=F("estoque") + item.quantidade)
        else:
            Produto.objects.filter(pk=item.produto_id).update(
                estoque=F("estoque") + item.quantidade)

    pedido.status = Pedido.Status.CANCELADO
    pedido.save(update_fields=["status"])
    return True
