from django.db import models
from django.contrib.auth.models import User
from produtos.models import Produto, Variante


class Pedido(models.Model):
    class Status(models.TextChoices):
        # "novo" já existia no banco; passa a se chamar "Pendente".
        # Nenhum pedido vira "Pago" sem confirmação (hoje, só manualmente no admin).
        NOVO = "novo", "Pendente"
        PAGO = "pago", "Pago"
        ENVIADO = "enviado", "Enviado"
        ENTREGUE = "entregue", "Entregue"
        CANCELADO = "cancelado", "Cancelado"

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    criado_em = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOVO)

    @property
    def total(self):
        # soma o subtotal de cada item do pedido
        return sum(item.subtotal for item in self.itens.all())

    @property
    def pode_cancelar(self):
        # só enquanto está pendente (ainda não pago nem enviado)
        return self.status == self.Status.NOVO


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, related_name="itens",
                               on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    variante = models.ForeignKey(Variante, null=True, blank=True,
                                 on_delete=models.PROTECT)
    # texto da variante no momento da compra (ex.: "A2 · Preto"), para o
    # histórico não mudar se a variante for editada depois
    descricao_variante = models.CharField(max_length=80, blank=True)
    quantidade = models.PositiveIntegerField(default=1)
    preco = models.DecimalField(max_digits=8, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantidade * self.preco
