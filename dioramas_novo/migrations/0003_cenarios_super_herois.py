from django.db import migrations


CENARIOS = {
    "arena": ("Arena Sakaar", "arena-sakaar", "Arena alienígena para confrontos épicos.", "Arena gladiatorial alienígena em miniatura, rocha, metal, arquibancadas industriais e luz cósmica colorida."),
    "castelo-medieval": ("Asgard", "asgard", "Reino dourado entre montanhas e estrelas.", "Palácio celestial dourado em miniatura, ponte de energia multicolorida, montanhas, cachoeiras e céu cósmico."),
    "cenario-cyberpunk": ("Distrito Cyberpunk", "distrito-cyberpunk", "Metrópole tecnológica iluminada por neon.", "Beco futurista em miniatura, chuva, trem elevado, neon magenta e ciano, vapor e arquitetura tecnológica."),
    "cidade-noturna": ("Nova York Noturna", "nova-york-noturna", "Coberturas e arranha-céus sob chuva.", "Cobertura de Nova York em miniatura à noite, art déco, chuva, ruas molhadas e iluminação cinematográfica."),
    "espaco-ficcao-cientifica": ("Base Cósmica", "base-cosmica", "Estação espacial diante de mundos distantes.", "Base espacial em miniatura, hangar avançado, planetas, nebulosa e iluminação ciano e violeta."),
    "floresta-mistica": ("Floresta Alienígena", "floresta-alienigena", "Selva bioluminescente de outro mundo.", "Floresta alienígena em miniatura, plantas bioluminescentes, ruínas, névoa e luas no céu."),
    "pos-apocaliptico": ("Nova York Pós-Batalha", "nova-york-pos-batalha", "Cidade danificada após um grande confronto.", "Avenida urbana em miniatura após grande batalha, concreto quebrado, fumaça, faíscas e luz dramática."),
    "templo-antigo": ("Dimensão Mística", "dimensao-mistica", "Santuário entre portais e estruturas impossíveis.", "Santuário místico em miniatura, arquitetura circular impossível, portais abstratos de luz âmbar e pedras flutuantes."),
    "laboratorio-futurista": ("Laboratório Tecnológico", "laboratorio-tecnologico", "Centro subterrâneo de tecnologia avançada.", "Laboratório subterrâneo em miniatura, aço, vidro, braços robóticos, hologramas abstratos e luz azul."),
    "ruinas": ("Wakanda Futurista", "wakanda-futurista", "Cidade avançada integrada à natureza.", "Cidade africana futurista em miniatura, torres elegantes, cachoeiras, vegetação e energia azul-violeta sutil."),
}


def atualizar(apps, schema_editor):
    Preset = apps.get_model("dioramas_novo", "DioramaPresetNovo")
    for slug_antigo, (nome, slug, descricao, prompt) in CENARIOS.items():
        Preset.objects.filter(slug=slug_antigo).update(nome=nome, slug=slug, descricao=descricao, prompt_base=prompt)


class Migration(migrations.Migration):
    dependencies = [("dioramas_novo", "0002_presets_iniciais")]
    operations = [migrations.RunPython(atualizar, migrations.RunPython.noop)]
