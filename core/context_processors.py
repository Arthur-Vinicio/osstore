from django.conf import settings

from produtos.models import Produto


def loja(request):
    """Dados de uso global nos templates: nome da loja, WhatsApp e categorias."""
    categorias = list(
        Produto.objects.filter(ativo=True)
        .order_by("categoria")
        .values_list("categoria", flat=True)
        .distinct()
    )
    return {
        "loja_nome": settings.LOJA_NOME,
        "loja_whatsapp": settings.WHATSAPP_NUMERO,   # vazio = sem botão
        "menu_categorias": categorias,
    }
