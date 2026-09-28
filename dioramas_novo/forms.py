from django import forms

from .models import DioramaGeradoNovo, DioramaPresetNovo


class ConfigurarDioramaForm(forms.Form):
    tipo = forms.ChoiceField(choices=DioramaGeradoNovo.TIPO_CHOICES, widget=forms.RadioSelect)
    preset = forms.ModelChoiceField(queryset=DioramaPresetNovo.objects.none(), required=False)
    descricao = forms.CharField(required=False, max_length=1500, widget=forms.Textarea(attrs={
        "rows": 6,
        "placeholder": "Ex.: Em cima de um prédio numa noite chuvosa, com cidade ao fundo, névoa e iluminação cinematográfica.",
    }))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["preset"].queryset = DioramaPresetNovo.objects.filter(ativo=True)

    def clean(self):
        dados = super().clean()
        if dados.get("tipo") == DioramaGeradoNovo.TIPO_PREDEFINIDO and not dados.get("preset"):
            self.add_error("preset", "Escolha um cenário predefinido.")
        if dados.get("tipo") == DioramaGeradoNovo.TIPO_PERSONALIZADO and not (dados.get("descricao") or "").strip():
            self.add_error("descricao", "Descreva como você imagina o diorama.")
        return dados
