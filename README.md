# OSStore

Loja virtual de equipamentos de jiu-jítsu (Django).

## Rodando localmente

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate        # IMPORTANTE: há migrações novas (produtos 0003, pedidos 0002, core 0002)
python manage.py runserver
```

Sem variáveis de ambiente o projeto roda em modo desenvolvimento (`DJANGO_DEBUG` assume `1`).

## Testes

```bash
python manage.py test
```

## Produção

Veja `.env.example`. Resumo:

- `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` e `DJANGO_ALLOWED_HOSTS` são obrigatórios (sem a chave o Django nem sobe).
- `python manage.py collectstatic` e sirva `staticfiles/` e `media/` pelo servidor web (nginx etc.);
  o Django só serve `media/` com `DEBUG=1`.
- Use PostgreSQL/MySQL: o travamento de estoque (`select_for_update`) não tem efeito no SQLite.
- O site **não processa pagamentos**. Pedidos nascem como *Pendente*; marcar como *Pago* é manual no admin.

## Cadastros no admin

- **Produtos**: descrição, características, material e tabela de medidas aparecem na página do produto só se preenchidos.
- **Variantes** (tamanho/cor com estoque próprio): inline dentro do produto. Com variantes ativas, o estoque do produto é ignorado.
- **Galeria**: imagens extras, inline dentro do produto.
- Para cancelar pedidos devolvendo estoque, use a ação "Cancelar pedidos pendentes selecionados". Mudar o status para *Cancelado* direto no formulário **não** devolve estoque.

## Capa da home

Para usar uma fotografia na capa, salve-a como `core/static/core/img/hero.jpg`. Sem ela, a capa usa o produto mais novo com foto.

## WhatsApp

Defina `OSSTORE_WHATSAPP` com o número real. Sem ele, nenhum botão é exibido. O botão apenas abre o WhatsApp com uma mensagem pronta.
