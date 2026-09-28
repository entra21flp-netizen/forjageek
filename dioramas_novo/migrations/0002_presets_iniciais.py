from django.db import migrations


PRESETS = [
    ("Cidade Noturna", "cidade-noturna", "Ambiente urbano noturno cinematográfico.", "Cidade em miniatura à noite, prédios altos, ruas molhadas, chuva leve, névoa e luzes cinematográficas."),
    ("Castelo Medieval", "castelo-medieval", "Fortaleza de pedra com atmosfera épica.", "Castelo medieval em miniatura, muralhas de pedra, tochas, salão épico e atmosfera dramática."),
    ("Espaço / Ficção Científica", "espaco-ficcao-cientifica", "Estação espacial e paisagem cósmica.", "Base espacial em miniatura, estrelas, planetas, painéis tecnológicos e iluminação azul cinematográfica."),
    ("Floresta Mística", "floresta-mistica", "Natureza encantada com luz etérea.", "Floresta mística em miniatura, árvores antigas, musgo, névoa, pequenos pontos de luz e atmosfera encantada."),
    ("Pós-Apocalíptico", "pos-apocaliptico", "Ruínas urbanas e sobrevivência.", "Cidade pós-apocalíptica em miniatura, concreto quebrado, veículos abandonados, poeira e luz dramática."),
    ("Templo Antigo", "templo-antigo", "Arquitetura ancestral monumental.", "Templo antigo em miniatura, colunas, inscrições abstratas sem texto legível, pedras gastas e raios de luz."),
    ("Laboratório Futurista", "laboratorio-futurista", "Tecnologia avançada e luz clínica.", "Laboratório futurista em miniatura, cápsulas, painéis luminosos sem texto, metal e luz branca e ciano."),
    ("Arena", "arena", "Palco épico para confronto.", "Arena monumental em miniatura, arquibancadas, piso detalhado, refletores e atmosfera de grande evento."),
    ("Ruínas", "ruinas", "Vestígios arquitetônicos tomados pelo tempo.", "Ruínas antigas em miniatura, arcos quebrados, pedras, vegetação discreta e luz dourada atravessando poeira."),
    ("Cenário Cyberpunk", "cenario-cyberpunk", "Metrópole tecnológica iluminada por neon.", "Beco cyberpunk em miniatura, neon magenta e ciano, chuva, cabos, vapor e arquitetura futurista sem textos."),
]


def criar_presets(apps, schema_editor):
    Preset = apps.get_model("dioramas_novo", "DioramaPresetNovo")
    for nome, slug, descricao, prompt in PRESETS:
        Preset.objects.update_or_create(slug=slug, defaults={"nome": nome, "descricao": descricao, "prompt_base": prompt, "ativo": True})


def remover_presets(apps, schema_editor):
    Preset = apps.get_model("dioramas_novo", "DioramaPresetNovo")
    Preset.objects.filter(slug__in=[item[1] for item in PRESETS]).delete()


class Migration(migrations.Migration):
    dependencies = [("dioramas_novo", "0001_initial")]
    operations = [migrations.RunPython(criar_presets, remover_presets)]
