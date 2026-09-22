from django import forms
from django.db import transaction
from catalogo.models import ModeloColecionavel, TipoColecionavel, Caracteristica, ModeloCaracteristica, ImagemModelo
from inventario.models import ColecionavelUsuario, ImagemColecionavel


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    widget = MultipleImageInput

    def clean(self, data, initial=None):
        files = data if isinstance(data, (list, tuple)) else [data] if data else []
        return [super(MultipleImageField, self).clean(file, initial) for file in files]


class CadastroColecionavelForm(forms.ModelForm):
    foto = MultipleImageField(required=False, label='Fotos do colecionável', widget=MultipleImageInput(attrs={'accept':'image/jpeg,image/png,image/webp'}))

    def clean_foto(self):
        fotos = self.cleaned_data.get('foto') or []
        if len(fotos) > 6:
            raise forms.ValidationError('Adicione no máximo 6 fotos por colecionável.')
        for foto in fotos:
            if foto.size > 10 * 1024 * 1024:
                raise forms.ValidationError('Cada imagem pode ter até 10 MB.')
            if foto.image.format not in ('JPEG', 'PNG', 'WEBP'):
                raise forms.ValidationError('Use apenas imagens JPG, PNG ou WebP.')
        return fotos
    modelo = forms.ModelChoiceField(queryset=ModeloColecionavel.objects.all(), required=False, empty_label='Cadastrar um novo modelo', label='Modelo do catálogo')
    tipo = forms.ModelChoiceField(queryset=TipoColecionavel.objects.all(), required=False, label='Categoria')
    nome_modelo = forms.CharField(max_length=255, required=False, label='Nome completo do modelo')
    nome_personagem = forms.CharField(max_length=255, required=False, label='Personagem')
    franquia = forms.CharField(max_length=255, required=False, label='Franquia')
    fabricante = forms.CharField(max_length=255, required=False, label='Fabricante')
    codigo_barras_ean_jan = forms.RegexField(r'^\d{8,13}$', max_length=13, required=False, label='Código de barras EAN / JAN / UPC')
    codigo_fabricante_sku = forms.CharField(max_length=100, required=False, label='Código do fabricante (SKU)')
    imagem_modelo = forms.URLField(max_length=500, required=False, label='URL da imagem do modelo')
    imagem_peca = forms.URLField(max_length=500, required=False, label='URL da imagem da sua peça')
    preco_pago = forms.DecimalField(max_digits=20, decimal_places=2, min_value=0, localize=True, label='Valor pago (R$)')
    preco_anunciado = forms.DecimalField(max_digits=20, decimal_places=2, min_value=0.01, localize=True, required=False, label='Preço anunciado (R$)')
    class Meta:
        model = ColecionavelUsuario
        fields = ['modelo','nome_personalizado','personalizado','estado_peca','condicao_caixa','nota','preco_pago','local_armazenamento','status_privacidade','status_negociacao','preco_anunciado','interesses_troca']
        labels = {'nome_personalizado':'Nome personalizado','personalizado':'Peça customizada','estado_peca':'Estado da peça','condicao_caixa':'Condição da caixa','nota':'Notas sobre a peça','local_armazenamento':'Local de armazenamento','status_privacidade':'Quem pode ver?','status_negociacao':'Disponibilidade','interesses_troca':'Interesses de troca'}
        widgets = {'nota':forms.Textarea(attrs={'rows':3}),'interesses_troca':forms.Textarea(attrs={'rows':3})}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.caracteristicas=list(Caracteristica.objects.exclude(tipos=None).prefetch_related('tipos').distinct())
        for c in self.caracteristicas:
            op=dict(label=c.nome_caracteristica,required=False)
            if c.tipo_dado=='boolean':
                f=forms.ChoiceField(choices=[('','Não informado'),('true','Sim'),('false','Não')],**op)
            elif c.tipo_dado=='numero':
                f=forms.DecimalField(max_digits=20,decimal_places=4,min_value=0,localize=True,**op)
            else:
                f=forms.CharField(max_length=255,**op)
            self.fields[f'car_{c.pk}']=f
    def clean(self):
        d=super().clean()
        if not d.get('modelo'):
            for f in ['nome_modelo','nome_personagem','franquia','fabricante','tipo']:
                if not d.get(f): self.add_error(f,'Preencha este campo para cadastrar um novo modelo.')
            code=d.get('codigo_barras_ean_jan')
            if code and ModeloColecionavel.objects.filter(codigo_barras_ean_jan=code).exists(): self.add_error('codigo_barras_ean_jan','Código já cadastrado. Selecione o modelo existente.')
        if d.get('status_negociacao') in ['venda','venda_ou_troca'] and d.get('preco_anunciado') is None: self.add_error('preco_anunciado','Informe o preço de venda.')
        if d.get('status_negociacao') not in ['venda','venda_ou_troca']: d['preco_anunciado']=None
        return d
    @transaction.atomic
    def save_for_user(self,user):
        item=super().save(commit=False)
        d=self.cleaned_data
        if not d.get('modelo'):
            values={k:d[k] for k in ['nome_modelo','nome_personagem','franquia','fabricante','tipo']}
            for k in ['codigo_barras_ean_jan','codigo_fabricante_sku']: values[k]=d.get(k) or None
            item.modelo=ModeloColecionavel.objects.create(**values)
            for c in self.caracteristicas:
                value=d.get(f'car_{c.pk}')
                if value not in (None,'') and d['tipo'] in c.tipos.all(): ModeloCaracteristica.objects.create(modelo=item.modelo,caracteristica=c,valor=str(value))
            if d.get('imagem_modelo'): ImagemModelo.objects.create(modelo=item.modelo,url_imagem=d['imagem_modelo'],imagem_principal=True)
        item.usuario=user
        item.save()
        if d.get('foto'):
            for ordem, foto in enumerate(d['foto']):
                ImagemColecionavel.objects.create(
                    colecionavel_usuario=item,
                    arquivo=foto,
                    ordem_exibicao=ordem,
                    imagem_principal=ordem == 0,
                )
        elif d.get('imagem_peca'):
            ImagemColecionavel.objects.create(colecionavel_usuario=item,url_imagem=d['imagem_peca'],imagem_principal=True)
        return item
    def sections(self):
        groups=[('Identificação do modelo','modelo-novo',['tipo','nome_modelo','nome_personagem','franquia','fabricante','codigo_barras_ean_jan','codigo_fabricante_sku','imagem_modelo']),('Sua peça','',['nome_personalizado','personalizado','estado_peca','condicao_caixa','preco_pago','local_armazenamento','nota','imagem_peca']),('Privacidade e negociação','',['status_privacidade','status_negociacao','preco_anunciado','interesses_troca'])]
        return [{'title':t,'id':i,'fields':[self[f] for f in fs]} for t,i,fs in groups]
    def characteristic_fields(self):
        return [{'field':self[f'car_{c.pk}'],'types':' '.join(str(t.pk) for t in c.tipos.all())} for c in self.caracteristicas]


class EditarColecionavelForm(forms.ModelForm):
    class Meta:
        model = ColecionavelUsuario
        fields = [
            'nome_personalizado', 'personalizado', 'estado_peca', 'condicao_caixa',
            'nota', 'preco_pago', 'local_armazenamento', 'status_privacidade',
            'status_negociacao', 'preco_anunciado', 'interesses_troca',
        ]
        labels = {
            'nome_personalizado': 'Nome personalizado',
            'personalizado': 'Peça customizada',
            'estado_peca': 'Estado da peça',
            'condicao_caixa': 'Condição da caixa',
            'nota': 'Notas sobre a peça',
            'preco_pago': 'Valor pago (R$)',
            'local_armazenamento': 'Local de armazenamento',
            'status_privacidade': 'Quem pode ver?',
            'status_negociacao': 'Disponibilidade',
            'preco_anunciado': 'Preço anunciado (R$)',
            'interesses_troca': 'Interesses de troca',
        }
        widgets = {
            'nota': forms.Textarea(attrs={'rows': 4}),
            'interesses_troca': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estado_peca'].widget.attrs['list'] = 'estados-peca'
        self.fields['condicao_caixa'].widget.attrs['list'] = 'condicoes-caixa'

    def clean(self):
        dados = super().clean()
        negociacao = dados.get('status_negociacao')
        if negociacao in ['venda', 'venda_ou_troca'] and dados.get('preco_anunciado') is None:
            self.add_error('preco_anunciado', 'Informe o preço de venda.')
        if negociacao not in ['venda', 'venda_ou_troca']:
            dados['preco_anunciado'] = None
        return dados
