from decimal import Decimal

from django.test import SimpleTestCase

from .views import _centavos


class ConversaoStripeTests(SimpleTestCase):
    def test_converte_reais_para_centavos_sem_erro_de_ponto_flutuante(self):
        self.assertEqual(_centavos(Decimal("129.90")), 12990)

    def test_arredonda_meio_centavo(self):
        self.assertEqual(_centavos(Decimal("10.005")), 1001)
