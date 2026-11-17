"""Testes do gráfico de contribuições.  Rode: python -m unittest discover -s ferramentas/testes"""
import sys
import unittest
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contribuicoes import estatisticas, ler_html, montar_svg, nivel, suave  # noqa: E402


def ano(contagens: dict[int, int], hoje=date(2026, 11, 17)):
    """365 dias terminando em `hoje`; contagens = {dias atrás: contagem}."""
    return [(hoje - timedelta(days=i), contagens.get(i, 0)) for i in range(364, -1, -1)]


class Estatisticas(unittest.TestCase):
    def test_total_e_sequencias(self):
        dias = ano({0: 3, 1: 2, 2: 1, 10: 5, 11: 5, 12: 5, 13: 5})
        e = estatisticas(dias)
        self.assertEqual(e["total"], 26)
        self.assertEqual(e["maior"], 4)
        self.assertEqual(e["atual"], 3)
        self.assertEqual(e["pico"], 5)

    def test_sequencia_atual_conta_ate_ontem_se_hoje_vazio(self):
        e = estatisticas(ano({1: 1, 2: 1}))
        self.assertEqual(e["atual"], 2)

    def test_ano_vazio(self):
        e = estatisticas(ano({}))
        self.assertEqual((e["total"], e["maior"], e["atual"]), (0, 0, 0))

    def test_nivel(self):
        self.assertEqual(nivel(0, 13), 0)
        self.assertEqual(nivel(1, 13), 1)
        self.assertEqual(nivel(13, 13), 4)
        self.assertEqual(nivel(7, 13), 3)


class Html(unittest.TestCase):
    def test_le_dias_e_contagens(self):
        html = (
            '<td data-date="2026-11-16" id="c-0" data-level="0"></td>'
            '<td data-date="2026-11-17" id="c-1" data-level="2"></td>'
            '<tool-tip for="c-0" class="x">No contributions on November 16th.</tool-tip>'
            '<tool-tip for="c-1" class="x">13 contributions on November 17th.</tool-tip>'
        )
        self.assertEqual(ler_html(html), [(date(2026, 11, 16), 0), (date(2026, 11, 17), 13)])

    def test_singular(self):
        html = '<td data-date="2026-06-22" id="a"></td><tool-tip for="a">1 contribution on June 22nd.</tool-tip>'
        self.assertEqual(ler_html(html), [(date(2026, 6, 22), 1)])


class Svg(unittest.TestCase):
    def test_svg_valido_com_um_ponto_por_dia_parado(self):
        dias = ano({0: 2, 5: 1, 40: 9})
        conteudo = montar_svg(dias)
        raiz = ET.fromstring(conteudo)
        self.assertTrue(raiz.tag.endswith("svg"))
        self.assertIn("prefers-reduced-motion", conteudo)
        # 365 dias, 3 com contribuição; hoje fica à parte → 362 pontinhos
        vazios = [e for e in raiz.iter() if e.get("id") == "vazios"][0]
        self.assertEqual(vazios.get("d").count("z"), 362)

    def test_hoje_vazio_fica_so_com_contorno(self):
        raiz = ET.fromstring(montar_svg(ano({3: 1})))
        hoje = [e for e in raiz.iter() if e.get("id") == "hoje"][0]
        self.assertEqual(hoje.get("fill"), "none")

    def test_hoje_com_contribuicao_fica_aceso(self):
        raiz = ET.fromstring(montar_svg(ano({0: 4})))
        hoje = [e for e in raiz.iter() if e.get("id") == "hoje"][0]
        self.assertNotEqual(hoje.get("fill"), "none")

    def test_curva_das_semanas_nao_afunda_abaixo_de_zero(self):
        pontos = [(0, 100), (10, 100), (20, 40), (30, 100), (40, 100)]  # y cresce para baixo; 100 = zero
        self.assertLessEqual(max(y for _, y in suave(pontos)), 100 + 1e-9)

    def test_ano_sem_contribuicoes_nao_quebra(self):
        ET.fromstring(montar_svg(ano({})))


if __name__ == "__main__":
    unittest.main()
