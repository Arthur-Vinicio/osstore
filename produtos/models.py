from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Produto(models.Model):
    nome = models.CharField(max_length=120)
    categoria = models.CharField(max_length=60)
    preco = models.DecimalField(max_digits=8, decimal_places=2)
    # Estoque do produto "simples". Se o produto tiver variantes ativas
    # (tamanho/cor), o estoque que vale é o de cada variante.
    estoque = models.PositiveIntegerField(default=0)
    ativo = models.BooleanField(default=True)
    imagem = models.ImageField(upload_to="produtos/", blank=True)

    descricao = models.TextField("descrição", blank=True)
    caracteristicas = models.TextField(
        "características", blank=True,
        help_text="Uma característica por linha.",
    )
    material = models.CharField(max_length=200, blank=True)
    tabela_medidas = models.TextField(
        "tabela de medidas", blank=True,
        help_text=(
            "Uma linha por tamanho, colunas separadas por | . A primeira linha "
            "é o cabeçalho. Ex.: Tamanho | Altura | Peso. Deixe vazio se o "
            "produto não usa tabela."
        ),
    )
    criado_em = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        # texto que aparece no admin e no shell
        return self.nome

    # --- variantes -------------------------------------------------------
    # Estes métodos percorrem `self.variantes.all()` em Python para aproveitar
    # prefetch_related("variantes") e evitar uma consulta por produto nas listas.

    def variantes_ativas(self):
        return [v for v in self.variantes.all() if v.ativo]

    @property
    def tem_variantes(self):
        return bool(self.variantes_ativas())

    @property
    def estoque_total(self):
        variantes = self.variantes_ativas()
        if variantes:
            return sum(v.estoque for v in variantes)
        return self.estoque

    @property
    def disponivel(self):
        return self.estoque_total > 0

    # --- conteúdo --------------------------------------------------------

    @property
    def lista_caracteristicas(self):
        return [l.strip() for l in self.caracteristicas.splitlines() if l.strip()]

    @property
    def linhas_tabela_medidas(self):
        linhas = []
        for linha in self.tabela_medidas.splitlines():
            if linha.strip():
                linhas.append([c.strip() for c in linha.split("|")])
        return linhas


class ImagemProduto(models.Model):
    """Imagens extras da galeria (a imagem principal continua em Produto.imagem)."""

    produto = models.ForeignKey(Produto, related_name="imagens", on_delete=models.CASCADE)
    imagem = models.ImageField(upload_to="produtos/galeria/")
    legenda = models.CharField(max_length=120, blank=True)
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "pk"]
        verbose_name = "imagem da galeria"
        verbose_name_plural = "imagens da galeria"

    def __str__(self):
        return self.legenda or f"Imagem {self.pk} de {self.produto}"


class Variante(models.Model):
    """Uma combinação comprável de um produto (ex.: A2 / Preto) com estoque próprio."""

    produto = models.ForeignKey(Produto, related_name="variantes", on_delete=models.CASCADE)
    tamanho = models.CharField(max_length=20, blank=True)
    cor = models.CharField(max_length=40, blank=True)
    estoque = models.PositiveIntegerField(default=0)
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "tamanho", "cor"]
        constraints = [
            models.UniqueConstraint(
                fields=["produto", "tamanho", "cor"], name="variante_unica_por_produto"
            ),
        ]

    def __str__(self):
        return self.rotulo

    @property
    def rotulo(self):
        return " · ".join(p for p in (self.tamanho, self.cor) if p) or "Padrão"

    def clean(self):
        if not self.tamanho.strip() and not self.cor.strip():
            raise ValidationError("Informe o tamanho, a cor ou ambos.")
