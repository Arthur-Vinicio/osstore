from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Produto, Variante


@override_settings(SECURE_SSL_REDIRECT=False)
class CatalogoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.kimono = Produto.objects.create(nome="Kimono Alfa", categoria="Kimono", preco=Decimal("500.00"), estoque=5)
        cls.faixa = Produto.objects.create(nome="Faixa Beta", categoria="Faixa", preco=Decimal("80.00"), estoque=10)
        cls.rash = Produto.objects.create(nome="Rashguard Gama", categoria="Rashguard", preco=Decimal("150.00"), estoque=3)
        cls.inativo = Produto.objects.create(nome="Oculto", categoria="Faixa", preco=Decimal("10.00"), estoque=1, ativo=False)

    def nomes(self, resp):
        return [p.nome for p in resp.context["produtos"]]

    def test_lista_mostra_so_ativos(self):
        resp = self.client.get(reverse("produtos"))
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("Oculto", self.nomes(resp))
        self.assertEqual(resp.context["total"], 3)

    def test_busca_por_nome(self):
        resp = self.client.get(reverse("produtos"), {"q": "beta"})
        self.assertEqual(self.nomes(resp), ["Faixa Beta"])

    def test_filtro_por_categoria(self):
        resp = self.client.get(reverse("produtos"), {"categoria": "kimono"})
        self.assertEqual(self.nomes(resp), ["Kimono Alfa"])

    def test_filtro_por_faixa_de_preco(self):
        resp = self.client.get(reverse("produtos"), {"preco_min": "100", "preco_max": "200,00"})
        self.assertEqual(self.nomes(resp), ["Rashguard Gama"])

    def test_preco_invalido_e_ignorado_sem_erro(self):
        for valor in ("abc", "NaN", "-5", "1e999999"):
            resp = self.client.get(reverse("produtos"), {"preco_min": valor})
            self.assertEqual(resp.status_code, 200, valor)
            self.assertEqual(resp.context["total"], 3, valor)

    def test_ordenacao_por_preco(self):
        asc = self.client.get(reverse("produtos"), {"ordem": "preco_asc"})
        desc = self.client.get(reverse("produtos"), {"ordem": "preco_desc"})
        self.assertEqual(self.nomes(asc), ["Faixa Beta", "Rashguard Gama", "Kimono Alfa"])
        self.assertEqual(self.nomes(desc), ["Kimono Alfa", "Rashguard Gama", "Faixa Beta"])

    def test_ordenacao_invalida_cai_no_padrao(self):
        resp = self.client.get(reverse("produtos"), {"ordem": "drop table"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["ordem"], "nome")

    def test_paginacao(self):
        for i in range(12):
            Produto.objects.create(nome=f"Extra {i:02d}", categoria="Extra", preco=Decimal("20.00"), estoque=1)
        p1 = self.client.get(reverse("produtos"))
        p2 = self.client.get(reverse("produtos"), {"page": 2})
        self.assertEqual(len(p1.context["produtos"]), 12)
        self.assertEqual(len(p2.context["produtos"]), 3)   # 15 ativos no total

    def test_detalhe_de_produto_ativo(self):
        resp = self.client.get(reverse("produto_detalhe", args=[self.kimono.pk]))
        self.assertContains(resp, "Kimono Alfa")

    def test_detalhe_de_produto_inativo_da_404(self):
        resp = self.client.get(reverse("produto_detalhe", args=[self.inativo.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_detalhe_mostra_variantes_e_bloqueia_esgotada(self):
        Variante.objects.create(produto=self.kimono, tamanho="A2", cor="Preto", estoque=4)
        Variante.objects.create(produto=self.kimono, tamanho="A3", cor="Preto", estoque=0)
        resp = self.client.get(reverse("produto_detalhe", args=[self.kimono.pk]))
        self.assertContains(resp, "A2 · Preto")
        self.assertContains(resp, "A3 · Preto")
        self.assertContains(resp, "Esgotado")


class ModeloProdutoTests(TestCase):
    def test_estoque_total_usa_variantes_ativas(self):
        p = Produto.objects.create(nome="K", categoria="Kimono", preco=Decimal("1"), estoque=99)
        self.assertEqual(p.estoque_total, 99)                       # sem variantes: estoque do produto
        Variante.objects.create(produto=p, tamanho="A1", estoque=2)
        Variante.objects.create(produto=p, tamanho="A2", estoque=3)
        Variante.objects.create(produto=p, tamanho="A3", estoque=50, ativo=False)
        p = Produto.objects.get(pk=p.pk)
        self.assertTrue(p.tem_variantes)
        self.assertEqual(p.estoque_total, 5)                        # só as ativas

    def test_tabela_de_medidas_e_caracteristicas(self):
        p = Produto(nome="K", categoria="K", preco=1,
                    tabela_medidas="Tamanho | Altura\nA1 | 1,60\n\nA2 | 1,70",
                    caracteristicas="Trançado\n\nReforçado ")
        self.assertEqual(p.linhas_tabela_medidas, [["Tamanho", "Altura"], ["A1", "1,60"], ["A2", "1,70"]])
        self.assertEqual(p.lista_caracteristicas, ["Trançado", "Reforçado"])


@override_settings(SECURE_SSL_REDIRECT=False)
class PermissoesProdutoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cliente = User.objects.create_user("cliente", password="x-Senha-123456")
        cls.equipe = User.objects.create_user("equipe", password="x-Senha-123456", is_staff=True)
        cls.produto = Produto.objects.create(nome="P", categoria="C", preco=Decimal("10"), estoque=1)

    def test_anonimo_nao_cadastra_nem_edita(self):
        for url in (reverse("produto_novo"), reverse("produto_editar", args=[self.produto.pk])):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_cliente_comum_nao_cadastra_nem_edita(self):
        self.client.force_login(self.cliente)
        for url in (reverse("produto_novo"), reverse("produto_editar", args=[self.produto.pk])):
            self.assertEqual(self.client.get(url).status_code, 302)
        resp = self.client.post(reverse("produto_novo"), {"nome": "X", "categoria": "Y", "preco": "1", "estoque": "1"})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Produto.objects.filter(nome="X").exists())

    def test_equipe_acessa_formulario(self):
        self.client.force_login(self.equipe)
        self.assertEqual(self.client.get(reverse("produto_novo")).status_code, 200)

    def test_preco_zero_e_recusado(self):
        self.client.force_login(self.equipe)
        resp = self.client.post(reverse("produto_novo"), {"nome": "X", "categoria": "Y", "preco": "0", "estoque": "1"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Produto.objects.filter(nome="X").exists())
