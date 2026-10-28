from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from produtos.models import Produto, Variante

from .models import ItemPedido, Pedido
from .servicos import cancelar_pedido


@override_settings(SECURE_SSL_REDIRECT=False)
class BaseCarrinho(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ana = User.objects.create_user("ana", password="x-Senha-123456")
        cls.bia = User.objects.create_user("bia", password="x-Senha-123456")
        cls.faixa = Produto.objects.create(nome="Faixa", categoria="Faixa", preco=Decimal("80.00"), estoque=10)
        cls.kimono = Produto.objects.create(nome="Kimono", categoria="Kimono", preco=Decimal("500.00"), estoque=0)
        cls.a2 = Variante.objects.create(produto=cls.kimono, tamanho="A2", cor="Preto", estoque=3)
        cls.a3 = Variante.objects.create(produto=cls.kimono, tamanho="A3", cor="Preto", estoque=0)

    def carrinho(self):
        return self.client.session.get("carrinho", {})

    def definir_carrinho(self, dados):
        sessao = self.client.session
        sessao["carrinho"] = dados
        sessao.save()

    def estoque(self, obj):
        return type(obj).objects.get(pk=obj.pk).estoque


class CarrinhoTests(BaseCarrinho):
    def test_adicionar_produto_simples(self):
        self.client.post(reverse("adicionar", args=[self.faixa.pk]), {"quantidade": "2"})
        self.assertEqual(self.carrinho(), {f"{self.faixa.pk}:0": 2})

    def test_adicionar_exige_post(self):
        resp = self.client.get(reverse("adicionar", args=[self.faixa.pk]))
        self.assertEqual(resp.status_code, 405)

    def test_produto_com_variantes_exige_escolha(self):
        resp = self.client.post(reverse("adicionar", args=[self.kimono.pk]), {"quantidade": "1"})
        self.assertRedirects(resp, reverse("produto_detalhe", args=[self.kimono.pk]))
        self.assertEqual(self.carrinho(), {})

    def test_adicionar_variante_valida(self):
        self.client.post(reverse("adicionar", args=[self.kimono.pk]), {"variante": self.a2.pk, "quantidade": "2"})
        self.assertEqual(self.carrinho(), {f"{self.kimono.pk}:{self.a2.pk}": 2})

    def test_variante_enviada_para_produto_sem_variantes_e_ignorada(self):
        self.client.post(reverse("adicionar", args=[self.faixa.pk]), {"variante": self.a2.pk})
        self.assertEqual(self.carrinho(), {f"{self.faixa.pk}:0": 1})

    def test_variante_de_outro_produto_e_recusada(self):
        outro = Produto.objects.create(nome="Rash", categoria="Rashguard", preco=Decimal("150.00"), estoque=0)
        Variante.objects.create(produto=outro, tamanho="M", estoque=5)
        # a2 pertence ao kimono, não ao rashguard
        resp = self.client.post(reverse("adicionar", args=[outro.pk]), {"variante": self.a2.pk})
        self.assertRedirects(resp, reverse("produto_detalhe", args=[outro.pk]))
        self.assertEqual(self.carrinho(), {})

    def test_variante_esgotada_nao_entra(self):
        self.client.post(reverse("adicionar", args=[self.kimono.pk]), {"variante": self.a3.pk})
        self.assertEqual(self.carrinho(), {})

    def test_quantidade_e_limitada_ao_estoque(self):
        self.client.post(reverse("adicionar", args=[self.kimono.pk]), {"variante": self.a2.pk, "quantidade": "50"})
        self.assertEqual(self.carrinho()[f"{self.kimono.pk}:{self.a2.pk}"], 3)

    def test_quantidade_invalida_vira_um(self):
        self.client.post(reverse("adicionar", args=[self.faixa.pk]), {"quantidade": "abc"})
        self.assertEqual(self.carrinho(), {f"{self.faixa.pk}:0": 1})
        self.client.post(reverse("adicionar", args=[self.faixa.pk]), {"quantidade": "-9"})
        self.assertEqual(self.carrinho(), {f"{self.faixa.pk}:0": 2})

    def test_produto_inativo_nao_entra(self):
        Produto.objects.filter(pk=self.faixa.pk).update(ativo=False)
        resp = self.client.post(reverse("adicionar", args=[self.faixa.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_alterar_mais_menos_remover(self):
        chave = f"{self.faixa.pk}:0"
        self.definir_carrinho({chave: 2})
        url = reverse("alterar_carrinho", args=[self.faixa.pk])
        self.client.post(url, {"acao": "mais", "variante": "0"})
        self.assertEqual(self.carrinho()[chave], 3)
        self.client.post(url, {"acao": "menos", "variante": "0"})
        self.assertEqual(self.carrinho()[chave], 2)
        self.client.post(url, {"acao": "remover", "variante": "0"})
        self.assertEqual(self.carrinho(), {})

    def test_mais_nao_passa_do_estoque_da_variante(self):
        chave = f"{self.kimono.pk}:{self.a2.pk}"
        self.definir_carrinho({chave: 3})
        self.client.post(reverse("alterar_carrinho", args=[self.kimono.pk]), {"acao": "mais", "variante": self.a2.pk})
        self.assertEqual(self.carrinho()[chave], 3)

    def test_carrinho_antigo_sem_variante_continua_funcionando(self):
        self.definir_carrinho({str(self.faixa.pk): 2})          # formato antigo: só o id
        resp = self.client.get(reverse("ver_carrinho"))
        self.assertEqual(resp.context["quantidade_total"], 2)
        self.assertEqual(resp.context["total"], Decimal("160.00"))

    def test_chaves_corrompidas_sao_ignoradas(self):
        self.definir_carrinho({"lixo": 1, "1:x": 1, "-4:0": 1, str(self.faixa.pk): "dois"})
        resp = self.client.get(reverse("ver_carrinho"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["itens"], [])

    def test_total_usa_preco_do_banco(self):
        self.definir_carrinho({f"{self.faixa.pk}:0": 3, f"{self.kimono.pk}:{self.a2.pk}": 1})
        resp = self.client.get(reverse("ver_carrinho"))
        self.assertEqual(resp.context["total"], Decimal("740.00"))

    def test_item_que_exige_variante_e_removido(self):
        self.definir_carrinho({f"{self.kimono.pk}:0": 1})
        resp = self.client.get(reverse("ver_carrinho"))
        self.assertEqual(resp.context["itens"], [])
        self.assertEqual(self.carrinho(), {})

    def test_contador_do_carrinho_no_cabecalho(self):
        self.definir_carrinho({f"{self.faixa.pk}:0": 4})
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.context["carrinho_qtd"], 4)


class CheckoutTests(BaseCarrinho):
    def finalizar(self):
        return self.client.post(reverse("finalizar"))

    def test_anonimo_vai_para_login(self):
        self.definir_carrinho({f"{self.faixa.pk}:0": 1})
        resp = self.finalizar()
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_get_nao_cria_pedido(self):
        self.client.force_login(self.ana)
        self.definir_carrinho({f"{self.faixa.pk}:0": 1})
        self.client.get(reverse("finalizar"))
        self.assertEqual(Pedido.objects.count(), 0)

    def test_finalizar_cria_pedido_pendente_e_baixa_estoque(self):
        self.client.force_login(self.ana)
        self.definir_carrinho({f"{self.faixa.pk}:0": 2, f"{self.kimono.pk}:{self.a2.pk}": 1})
        resp = self.finalizar()
        pedido = Pedido.objects.get()
        self.assertRedirects(resp, reverse("pedido_detalhe", args=[pedido.pk]))
        self.assertEqual(pedido.usuario, self.ana)
        self.assertEqual(pedido.status, Pedido.Status.NOVO)           # nunca "pago" automaticamente
        self.assertEqual(pedido.total, Decimal("660.00"))
        self.assertEqual(self.estoque(self.faixa), 8)
        self.assertEqual(self.estoque(self.a2), 2)
        self.assertEqual(self.estoque(self.kimono), 0)                # estoque do produto-pai não muda
        item = pedido.itens.get(variante=self.a2)
        self.assertEqual(item.descricao_variante, "A2 · Preto")
        self.assertEqual(self.carrinho(), {})

    def test_preco_enviado_pelo_navegador_e_ignorado(self):
        self.client.force_login(self.ana)
        self.definir_carrinho({f"{self.faixa.pk}:0": 1})
        self.client.post(reverse("finalizar"), {"preco": "0.01", "total": "0.01"})
        self.assertEqual(ItemPedido.objects.get().preco, Decimal("80.00"))

    def test_estoque_insuficiente_bloqueia_tudo(self):
        self.client.force_login(self.ana)
        self.definir_carrinho({f"{self.faixa.pk}:0": 2, f"{self.kimono.pk}:{self.a2.pk}": 4})   # A2 só tem 3
        self.finalizar()
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertEqual(self.estoque(self.faixa), 10)                # nada foi baixado (tudo ou nada)
        self.assertEqual(self.estoque(self.a2), 3)

    def test_produto_desativado_depois_de_entrar_no_carrinho(self):
        self.client.force_login(self.ana)
        self.definir_carrinho({f"{self.faixa.pk}:0": 1})
        Produto.objects.filter(pk=self.faixa.pk).update(ativo=False)
        self.finalizar()
        self.assertEqual(Pedido.objects.count(), 0)

    def test_carrinho_vazio_nao_cria_pedido(self):
        self.client.force_login(self.ana)
        self.finalizar()
        self.assertEqual(Pedido.objects.count(), 0)


class PedidoPermissoesECancelamentoTests(BaseCarrinho):
    def criar_pedido(self, usuario, qtd=2, status=Pedido.Status.NOVO):
        self.client.force_login(usuario)
        self.definir_carrinho({f"{self.faixa.pk}:0": qtd})
        self.client.post(reverse("finalizar"))
        pedido = Pedido.objects.filter(usuario=usuario).latest("pk")
        if status != Pedido.Status.NOVO:
            Pedido.objects.filter(pk=pedido.pk).update(status=status)
        self.client.logout()
        return pedido

    def test_cada_usuario_ve_so_os_proprios_pedidos(self):
        pedido_ana = self.criar_pedido(self.ana)
        self.client.force_login(self.bia)
        self.assertEqual(self.client.get(reverse("pedido_detalhe", args=[pedido_ana.pk])).status_code, 404)
        lista = self.client.get(reverse("meus_pedidos"))
        self.assertEqual(list(lista.context["pedidos"]), [])
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(reverse("pedido_detalhe", args=[pedido_ana.pk])).status_code, 200)

    def test_anonimo_nao_ve_pedidos(self):
        pedido = self.criar_pedido(self.ana)
        self.assertEqual(self.client.get(reverse("pedido_detalhe", args=[pedido.pk])).status_code, 302)
        self.assertEqual(self.client.get(reverse("meus_pedidos")).status_code, 302)

    def test_cancelar_devolve_estoque(self):
        pedido = self.criar_pedido(self.ana, qtd=2)
        self.assertEqual(self.estoque(self.faixa), 8)
        self.client.force_login(self.ana)
        self.client.post(reverse("pedido_cancelar", args=[pedido.pk]))
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.CANCELADO)
        self.assertEqual(self.estoque(self.faixa), 10)

    def test_cancelar_devolve_estoque_da_variante(self):
        self.client.force_login(self.ana)
        self.definir_carrinho({f"{self.kimono.pk}:{self.a2.pk}": 2})
        self.client.post(reverse("finalizar"))
        pedido = Pedido.objects.get()
        self.assertEqual(self.estoque(self.a2), 1)
        self.client.post(reverse("pedido_cancelar", args=[pedido.pk]))
        self.assertEqual(self.estoque(self.a2), 3)

    def test_cancelar_duas_vezes_nao_devolve_estoque_em_dobro(self):
        pedido = self.criar_pedido(self.ana, qtd=2)
        self.assertTrue(cancelar_pedido(pedido.pk))
        self.assertFalse(cancelar_pedido(pedido.pk))
        self.assertEqual(self.estoque(self.faixa), 10)

    def test_nao_cancela_pedido_de_outro_usuario(self):
        pedido = self.criar_pedido(self.ana)
        self.client.force_login(self.bia)
        resp = self.client.post(reverse("pedido_cancelar", args=[pedido.pk]))
        self.assertEqual(resp.status_code, 404)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.NOVO)
        self.assertFalse(cancelar_pedido(pedido.pk, usuario=self.bia))

    def test_pedido_pago_nao_pode_ser_cancelado_pelo_cliente(self):
        pedido = self.criar_pedido(self.ana, qtd=2, status=Pedido.Status.PAGO)
        self.client.force_login(self.ana)
        self.client.post(reverse("pedido_cancelar", args=[pedido.pk]))
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.PAGO)
        self.assertEqual(self.estoque(self.faixa), 8)

    def test_cancelar_exige_post(self):
        pedido = self.criar_pedido(self.ana)
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(reverse("pedido_cancelar", args=[pedido.pk])).status_code, 405)
