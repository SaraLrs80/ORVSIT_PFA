"""
La vérification de la reformulation — la garantie centrale de l'assistant.

POURQUOI CES TESTS EN PREMIER
C'est la seule fonction qui empêche une invention d'atteindre l'utilisateur.
Tout le reste de l'architecture réduit le risque ; celle-ci le coupe. Si elle
cesse de rejeter, l'assistant peut afficher un chiffre que personne n'a
publié, avec une source officielle en dessous.

Les 270 questions du jeu d'évaluation ne la testent pas isolément : elles
notent la branche empruntée, pas la fidélité de la phrase finale. Ces tests
comblent exactement cet angle mort.
"""

import unittest

from tests import contexte  # noqa: F401  (fixe le chemin d'import)
from app.assistant.moteur import _verifier


class Verification(unittest.TestCase):

    def test_reformulation_fidele_acceptee(self):
        """Une mise en français qui ne touche à rien doit passer."""
        brouillon = "Taux de chômage pour Al Hoceima : 24,6 %, millésime 2024."
        phrase = ("Le taux de chômage de la province d'Al Hoceima s'élève à "
                  "24,6 % en 2024.")
        accepte, motif = _verifier(brouillon, phrase)
        self.assertTrue(accepte, f"rejetée à tort : {motif}")

    def test_nombre_invente_rejete(self):
        """Un chiffre absent du brouillon est une invention."""
        brouillon = "Taux de chômage pour Al Hoceima : 24,6 %, millésime 2024."
        phrase = ("Le taux de chômage atteint 24,6 % en 2024, contre 18,2 % "
                  "en 2014.")
        accepte, motif = _verifier(brouillon, phrase)
        self.assertFalse(accepte)
        self.assertIn("inventé", motif.lower())

    def test_nombre_perdu_rejete(self):
        """Un chiffre du brouillon absent de la phrase est une perte."""
        brouillon = ("Population légale de Tétouan : 605 000 habitants, "
                     "millésime 2024.")
        phrase = "Tétouan compte une population importante en 2024."
        accepte, motif = _verifier(brouillon, phrase)
        self.assertFalse(accepte)
        self.assertIn("perdu", motif.lower())

    def test_interpretation_ajoutee_rejetee(self):
        """Le modèle rend une phrase, pas une analyse.

        Ce cas est le plus insidieux : aucun chiffre ne bouge, et seule une
        détection sur le vocabulaire d'interprétation l'attrape.
        """
        brouillon = ("Population de Tétouan : 605 000 habitants ; population "
                     "de Larache : 507 000 habitants.")
        phrase = ("Tétouan compte 605 000 habitants et Larache 507 000, ce qui "
                  "souligne l'équilibre démographique de la région.")
        accepte, motif = _verifier(brouillon, phrase)
        self.assertFalse(accepte)
        self.assertIn("interprétation", motif.lower())

    def test_interpretation_conjuguee_rejetee(self):
        """Le participe présent doit être attrapé comme la forme conjuguée.

        Une liste de conjugaisons laissait passer « soulignant » là où elle
        arrêtait « souligne ». La détection porte donc sur le radical.
        """
        brouillon = "Taux d'activité pour Ouezzane : 41,3 %."
        for forme in ("soulignant une faiblesse", "soulignait un écart",
                      "révélant un écart", "révélait une faiblesse",
                      "témoignant d'un recul", "témoigné d'un recul"):
            with self.subTest(forme=forme):
                phrase = f"Le taux d'activité d'Ouezzane est de 41,3 %, {forme}."
                accepte, motif = _verifier(brouillon, phrase)
                self.assertFalse(accepte, f"« {forme} » n'a pas été détecté")

    def test_vocabulaire_deja_present_dans_le_brouillon_tolere(self):
        """On ne rejette pas un mot que le brouillon employait lui-même.

        Certains libellés contiennent « tendance » ou « équilibre » : les
        interdire sans regarder le brouillon rendrait ces indicateurs
        inaccessibles à la reformulation.
        """
        brouillon = ("Indice d'équilibre du logement pour Tanger-Assilah : "
                     "1,4.")
        phrase = "L'indice d'équilibre du logement de Tanger-Assilah vaut 1,4."
        accepte, motif = _verifier(brouillon, phrase)
        self.assertTrue(accepte, f"rejetée à tort : {motif}")

    def test_meme_nombre_ecrit_autrement(self):
        """L'espace des milliers ne doit pas passer pour un autre nombre."""
        brouillon = "Population légale de Tanger-Assilah : 1 275 428 habitants."
        phrase = "Tanger-Assilah compte 1 275 428 habitants."
        accepte, motif = _verifier(brouillon, phrase)
        self.assertTrue(accepte, f"rejetée à tort : {motif}")


if __name__ == "__main__":
    unittest.main()
