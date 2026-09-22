from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from inventario.models import ColecionavelUsuario, ImagemColecionavel
from usuarios.models import Usuario


IMAGENS = {
    "S.H.Figuarts Super Saiyan Full Power SON GOKU": [
        "https://tamashiiweb.com/storage/images/products/imported/item_0000013505_WeELih0m_01.jpg",
        "https://tamashiiweb.com/storage/images/products/imported/item_0000013505_WeELih0m_03.jpg",
    ],
    "S.H.Figuarts VEGETA <Z-FIGHTERS>": [
        "https://tamashiiweb.com/storage/images/products/main/3e66cac0-6c05-40ff-b16e-cb8734951f52.webp",
        "https://tamashiiweb.com/storage/images/products/sub/47114e71-588e-4028-bd40-40c0a81ae508.webp",
    ],
    "S.H.Figuarts Trunks <Z-FIGHTERS>": [
        "https://tamashiiweb.com/storage/images/products/main/e30bced7-51de-4dad-b2c5-6296bfa7d191.webp",
        "https://tamashiiweb.com/storage/images/products/sub/f60316de-f813-4fb5-ab2d-4965cef4dff7.webp",
    ],
    "S.H.Figuarts NARUTO UZUMAKI -The Hope Entrusted to the Nine-Tailed Fox Jinchuriki-": [
        "https://tamashiiweb.com/storage/images/products/imported/item_0000013853_t6frueHd_01.jpg",
        "https://tamashiiweb.com/storage/images/products/imported/item_0000013853_rlp9mq2W_03.jpg",
    ],
    "S.H.Figuarts SASUKE UCHIHA -He who bears all Hatred-": [
        "https://tamashiiweb.com/storage/images/products/imported/item_0000013854_oWV22YuJ_01.jpg",
        "https://tamashiiweb.com/storage/images/products/imported/item_0000013854_4EnS8lAw_03.jpg",
    ],
    "S.H.Figuarts KAKASHI HATAKE -The Legendary Hero of the Sharingan-": [
        "https://tamashiiweb.com/storage/images/products/imported/item_0000014030_5rj3LTrK_01.jpg",
        "https://tamashiiweb.com/storage/images/products/imported/item_0000014030_7fVlipNr_03.jpg",
    ],
    "HGUC 1/144 RX-78-2 Gundam": [
        "https://www.gundamplanet.com/cdn/shop/files/hguc-rx-78-2-gundam-01.jpg?v=1737658705",
        "https://www.gundamplanet.com/cdn/shop/files/hguc-rx-78-2-gundam-02.jpg?v=1737658705",
    ],
    "HG 1/144 Gundam Sandrock Custom EW": [
        "https://www.gundamplanet.com/cdn/shop/files/hgac-xxxg-01sr2-gundam-sandrock-custom-ew-ver-base.jpg?v=1780335427&width=1946",
        "https://www.gundamplanet.com/cdn/shop/files/hgac-xxxg-01sr2-gundam-sandrock-custom-ew-ver-01.jpg?v=1780334074&width=1946",
    ],
    "Bandai HGUC MS-06R-2 Zaku II Johnny Ridden Custom": [
        "https://www.gundamplanet.com/cdn/shop/files/rg-ms-06r-2-zaku-ii-johnny-ridden-custom-00_1.jpg?v=1737669636",
        "https://www.gundamplanet.com/cdn/shop/files/rg-ms-06r-2-zaku-ii-johnny-ridden-custom-01.jpg?v=1737669638",
    ],
    "Saint Seiya Champion Class Pegasus Seiya": [
        "https://blokees.com/cdn/shop/files/1_bbca6a2e-cfef-46f0-802e-5a52fc0a59cc.png?v=1754728511",
        "https://blokees.com/cdn/shop/files/2100_1_a4b4bbe5-de3b-469b-96f5-d5e3283a241b.png?v=1754728533",
    ],
    "Saint Seiya Champion Class Dragon Shiryu": [
        "https://blokees.com/cdn/shop/files/21_1e713021-3419-4be9-9613-f8edd71a9936.webp?v=1768893010",
        "https://blokees.com/cdn/shop/files/4511.webp?v=1768893010",
    ],
    "Saint Seiya Champion Class Cygnus Hyoga": [
        "https://blokees.com/cdn/shop/files/104_c14f2bab-f3b4-4c2a-99dc-8de788bac5b2.png?v=1763608152",
        "https://blokees.com/cdn/shop/files/11_6dd5a5ed-1574-4a99-b85d-30f4cd06e00f.png?v=1763608152",
    ],
    "Funko Pop! Spider-Man #03": [
        "https://i5.walmartimages.com/asr/eaa2b211-92bc-4294-b2d6-f5d3f802c767.61fcf6b28ac13e10fb176fbbd378425e.jpeg?odnBg=FFFFFF&odnHeight=900&odnWidth=900",
        "https://i5.walmartimages.com/asr/6bbda936-2437-4a6b-9677-0c7c519ce921.41059a54d84d2a63149f53cbfb435317.jpeg?odnBg=FFFFFF&odnHeight=900&odnWidth=900",
    ],
    "Funko Pop! Iron Man #04": [
        "https://pops.today/images/POP_MARVEL/Marvel%2B04_500x500.webp",
        "https://pops.today/images/POP_MARVEL/Marvel%2B04_160x160.webp",
    ],
    "Funko Pop! Captain America #06": [
        "https://pops.today/images/POP_MARVEL/Marvel%2B06_500x500.webp",
        "https://pops.today/images/POP_MARVEL/Marvel%2B06_160x160.webp",
    ],
    "Funko Pop! Naruto #71": [
        "https://draxu.com/cdn/shop/products/a-naruto-a.png?v=1672365533&width=1200",
        "https://draxu.com/cdn/shop/products/b-naruto.png?v=1672365533&width=1200",
    ],
    "Funko Pop! Sasuke #72": [
        "https://draxu.com/cdn/shop/products/a-sasuke-a.png?v=1672365349&width=1200",
        "https://draxu.com/cdn/shop/products/c-sasuke-a.png?v=1672365349&width=1200",
    ],
    "Funko Pop! Goku #09": [
        "https://pops.today/images/POP_ANIMATION/Dragon%2BBall%2BZ%2B09_500x500.webp",
        "https://pops.today/images/POP_ANIMATION/Dragon%2BBall%2BZ%2B09_160x160.webp",
    ],
    "Figuarts ZERO UCHIHA MADARA -ISOU SUSANOO- Kizuna Relation": [
        "https://tamashiiweb.com/storage/images/products/imported/item_0000012791_qx1wjXYV_01.jpg",
        "https://tamashiiweb.com/storage/images/products/imported/item_0000012791_qx1wjXYV_03.jpg",
    ],
    "Figuarts ZERO Sasuke Bond Relation": [
        "https://tamashiiweb.com/storage/images/products/imported/item_0000011807_ySgBPTIA_01.jpg",
        "https://tamashiiweb.com/storage/images/products/imported/item_0000011807_ySgBPTIA_03.jpg",
    ],
    "Figuarts ZERO Super Saiyan Gogeta": [
        "https://tamashiiweb.com/storage/images/products/imported/item_0000012230_bjP52mku_01.jpg",
        "https://tamashiiweb.com/storage/images/products/imported/item_0000012230_bjP52mku_03.jpg",
    ],
    "Figuarts ZERO Super Saiyan 3 Son Goku -Dragon fist explosion-": [
        "https://tamashiiweb.com/storage/images/products/imported/item_0000014623_Dc3OeMNR_01.jpg",
        "https://tamashiiweb.com/storage/images/products/imported/item_0000014623_wVNtjjCZ_03.jpg",
    ],
    "Figuarts ZERO Tanjiro Kamado Rengoku Guard ver.": [
        "https://tamashiiweb.com/storage/images/products/imported/item_0000015284_KkPmx64D_01.jpg",
        "https://tamashiiweb.com/storage/images/products/imported/item_0000015284_E35mw4ye_03.jpg",
    ],
    "Figuarts ZERO NARUTO UZUMAKI -NARUTO 72 series-": [
        "https://tamashiiweb.com/storage/images/products/imported/item_0000015358_Fm8zDns0_01.jpg",
        "https://tamashiiweb.com/storage/images/products/imported/item_0000015358_P1mGfe0P_03.jpg",
    ],
}


class Command(BaseCommand):
    help = "Adiciona duas imagens de demonstração aos 24 itens importados do Neon."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", default="rafageek")

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            usuario = Usuario.objects.get(username=options["usuario"])
        except Usuario.DoesNotExist as exc:
            raise CommandError("Usuário não encontrado.") from exc

        itens = ColecionavelUsuario.objects.filter(
            usuario=usuario, nota__startswith="Importado do catálogo Neon"
        ).select_related("modelo")
        encontrados = {item.modelo.nome_modelo: item for item in itens}
        ausentes = sorted(set(IMAGENS) - set(encontrados))
        if ausentes:
            raise CommandError("Modelos importados não encontrados: " + "; ".join(ausentes))

        total = 0
        for nome, urls in IMAGENS.items():
            item = encontrados[nome]
            item.imagens.all().delete()
            for ordem, url in enumerate(urls):
                ImagemColecionavel.objects.create(
                    colecionavel_usuario=item,
                    url_imagem=url,
                    ordem_exibicao=ordem,
                    imagem_principal=ordem == 0,
                )
                total += 1

        self.stdout.write(self.style.SUCCESS(f"{total} imagens adicionadas a {len(IMAGENS)} colecionáveis de {usuario.username}."))
