from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from pedidos.models import ItemPedido, Pedido
from produtos.models import Produto


@override_settings(SECURE_SSL_REDIRECT=False)
class HomeTests(TestCase):
    def test_home_sem_produtos_abre(self):
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Comprar agora")
        self.assertContains(resp, "Explorar coleção")
        self.assertContains(resp, "Nenhum produto cadastrado ainda.")

    def test_mais_vendidos_so_com_vendas_reais_suficientes(self):
        usuario = User.objects.create_user("u", password="x-Senha-123456")
        produtos = [Produto.objects.create(nome=f"P{i}", categoria="C", preco=Decimal("10"), estoque=5) for i in range(3)]
        self.assertNotContains(self.client.get(reverse("home")), "Mais vendidos")

        pedido = Pedido.objects.create(usuario=usuario, status=Pedido.Status.CANCELADO)
        for p in produtos:
            ItemPedido.objects.create(pedido=pedido, produto=p, quantidade=1, preco=p.preco)
        # pedido cancelado não conta como venda
        self.assertNotContains(self.client.get(reverse("home")), "Mais vendidos")

        Pedido.objects.filter(pk=pedido.pk).update(status=Pedido.Status.PAGO)
        self.assertContains(self.client.get(reverse("home")), "Mais vendidos")

    def test_rodape_so_mostra_whatsapp_quando_configurado(self):
        self.assertNotContains(self.client.get(reverse("home")), "wa.me")
        with override_settings(WHATSAPP_NUMERO="5521999990000"):
            self.assertContains(self.client.get(reverse("home")), "https://wa.me/5521999990000")


@override_settings(SECURE_SSL_REDIRECT=False)
class ContaTests(TestCase):
    def test_cadastro_cria_usuario_comum_mesmo_com_campos_extras(self):
        resp = self.client.post(reverse("cadastro"), {
            "username": "novo", "password1": "Senha-Forte-98123", "password2": "Senha-Forte-98123",
            "is_staff": "on", "is_superuser": "on",
        })
        self.assertEqual(resp.status_code, 302)
        usuario = User.objects.get(username="novo")
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)

    def test_cadastro_ignora_destino_externo(self):
        resp = self.client.post(reverse("cadastro") + "?next=https://malicioso.example/", {
            "username": "novo2", "password1": "Senha-Forte-98123", "password2": "Senha-Forte-98123",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn("malicioso", resp.url)

    def test_painel_exige_login(self):
        self.assertEqual(self.client.get(reverse("painel")).status_code, 302)

    def test_painel_para_usuario_logado(self):
        usuario = User.objects.create_user("logado", password="x-Senha-123456")
        self.client.force_login(usuario)
        self.assertContains(self.client.get(reverse("painel")), "logado")

    def test_login_e_logout(self):
        User.objects.create_user("maria", password="x-Senha-123456")
        resp = self.client.post(reverse("login"), {"username": "maria", "password": "x-Senha-123456"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_por_get_nao_funciona(self):
        usuario = User.objects.create_user("maria2", password="x-Senha-123456")
        self.client.force_login(usuario)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)

    def test_alterar_senha_exige_login_e_usa_template_da_loja(self):
        self.assertEqual(self.client.get(reverse("password_change")).status_code, 302)
        usuario = User.objects.create_user("troca", password="x-Senha-123456")
        self.client.force_login(usuario)
        self.assertTemplateUsed(self.client.get(reverse("password_change")), "registration/password_change_form.html")
