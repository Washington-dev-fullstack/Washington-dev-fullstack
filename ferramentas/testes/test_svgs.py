"""Confere os SVGs gerados: XML válido, leves, fontes embutidas e "reduzir movimento"."""
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from identidade import ASSETS  # noqa: E402

LIMITE_KB = 200  # o GitHub serve qualquer tamanho, mas leve = abre rápido no perfil


class SvgsGerados(unittest.TestCase):
    def setUp(self):
        self.arquivos = sorted(ASSETS.glob("*.svg"))
        self.assertTrue(self.arquivos, "rode ferramentas/gerar.py antes")

    def test_xml_valido(self):
        for a in self.arquivos:
            with self.subTest(a.name):
                ET.parse(a)

    def test_leves(self):
        for a in self.arquivos:
            with self.subTest(a.name):
                self.assertLess(a.stat().st_size / 1024, LIMITE_KB)

    def test_fontes_embutidas_e_sem_recurso_externo(self):
        for a in self.arquivos:
            with self.subTest(a.name):
                s = a.read_text(encoding="utf-8")
                self.assertIn("@font-face", s)
                # o SVG como imagem não carrega nada de fora: tudo tem de ser data URI
                externos = re.findall(r'(?:href|src)="(?!data:|#)([^"]+)"', s) + re.findall(r"url\((?!data:|#)", s)
                self.assertEqual(externos, [])

    def test_reduzir_movimento(self):
        for a in self.arquivos:
            with self.subTest(a.name):
                self.assertIn("prefers-reduced-motion:reduce", a.read_text(encoding="utf-8"))

    def test_so_anima_transform_e_opacity(self):
        """Animação leve: nada de filtro, desfoque ou propriedade que force layout."""
        for a in self.arquivos:
            with self.subTest(a.name):
                s = a.read_text(encoding="utf-8")
                self.assertNotIn("filter", s)
                for quadro in re.findall(r"@keyframes \w+\{(.*?\}\})", s):
                    props = set(re.findall(r"([a-z-]+):", quadro))
                    self.assertLessEqual(props, {"transform", "opacity", "fill-opacity"}, a.name)


if __name__ == "__main__":
    unittest.main()
