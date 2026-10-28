from django.contrib import admin, messages

from .models import Pedido, ItemPedido
from .servicos import cancelar_pedido


class ItemInline(admin.TabularInline):
    model = ItemPedido
    extra = 0


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "status", "criado_em")
    list_filter = ("status",)
    inlines = [ItemInline]
    actions = ["cancelar_e_devolver_estoque"]

    @admin.action(description="Cancelar pedidos pendentes selecionados (devolve o estoque)")
    def cancelar_e_devolver_estoque(self, request, queryset):
        feitos = sum(cancelar_pedido(pk) for pk in queryset.values_list("pk", flat=True))
        ignorados = queryset.count() - feitos
        self.message_user(request, f"{feitos} pedido(s) cancelado(s).", messages.SUCCESS)
        if ignorados:
            self.message_user(
                request,
                f"{ignorados} ignorado(s): só pedidos pendentes podem ser cancelados por aqui.",
                messages.WARNING,
            )
