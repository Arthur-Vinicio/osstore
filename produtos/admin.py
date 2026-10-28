from django.contrib import admin

from .models import ImagemProduto, Produto, Variante


class VarianteInline(admin.TabularInline):
    model = Variante
    extra = 0
    fields = ("tamanho", "cor", "estoque", "ativo", "ordem")


class ImagemInline(admin.TabularInline):
    model = ImagemProduto
    extra = 0
    fields = ("imagem", "legenda", "ordem")


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "preco", "estoque", "estoque_variantes", "ativo", "criado_em")
    list_filter = ("categoria", "ativo")
    search_fields = ("nome", "categoria")
    inlines = [VarianteInline, ImagemInline]
    fieldsets = (
        (None, {"fields": ("nome", "categoria", "preco", "ativo", "imagem")}),
        ("Estoque", {
            "fields": ("estoque",),
            "description": "Usado só quando o produto NÃO tem variantes ativas. "
                           "Com variantes (tamanho/cor), o estoque é controlado em cada variante.",
        }),
        ("Detalhes", {"fields": ("descricao", "caracteristicas", "material", "tabela_medidas")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("variantes")

    @admin.display(description="Estoque das variantes")
    def estoque_variantes(self, obj):
        return obj.estoque_total if obj.tem_variantes else "—"
