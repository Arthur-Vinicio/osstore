from django import forms
from .models import Produto


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ["nome", "categoria", "preco", "estoque", "ativo", "imagem",
                  "descricao", "caracteristicas", "material", "tabela_medidas"]
        labels = {
            "nome": "Nome do produto",
            "categoria": "Categoria",
            "preco": "Preço (R$)",
            "estoque": "Quantidade em estoque",
            "ativo": "Produto disponível na loja",
            "imagem": "Imagem do produto",
            "descricao": "Descrição",
            "caracteristicas": "Características",
            "material": "Material",
            "tabela_medidas": "Tabela de medidas",
        }
        help_texts = {
            "nome": "Use um nome claro para o cliente identificar o produto.",
            "categoria": "Ex.: Kimono, Rashguard, Faixa.",
            "estoque": "Usado só se o produto não tiver variantes (tamanho/cor). Variantes e galeria são cadastradas na Administração.",
            "imagem": "Formatos comuns de imagem são aceitos.",
        }
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex.: Kimono Jiu-Jitsu Classic Preto"}),
            "categoria": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex.: Kimono"}),
            "preco": forms.NumberInput(attrs={"class": "form-control", "placeholder": "0,00", "min": "0.01", "step": "0.01"}),
            "estoque": forms.NumberInput(attrs={"class": "form-control", "placeholder": "0", "min": "0", "step": "1"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "imagem": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*", "id": "id_imagem"}),
            "descricao": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "caracteristicas": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "material": forms.TextInput(attrs={"class": "form-control"}),
            "tabela_medidas": forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "Tamanho | Altura | Peso"}),
        }

    def clean_preco(self):
        preco = self.cleaned_data["preco"]
        if preco <= 0:
            raise forms.ValidationError("O preço deve ser maior que zero.")
        return preco
