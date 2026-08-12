"""
La reconnaissance de l'intention — le premier aiguillage.

CE QU'ELLE DÉCIDE
De l'intention dépend tout le reste : ce qu'il faut réunir, quel outil
appeler, et si un territoire est nécessaire. Une intention mal reconnue ne
produit pas une réponse approximative, elle produit la mauvaise réponse — un
classement là où une valeur était demandée, ou une demande de précision là où
la question était complète.

Les cas retenus ici sont ceux où deux intentions se ressemblent. Les cas
évidents n'apprennent rien.
"""

import unittest

from tests import contexte

contexte.brancher()

from app.assistant.moteur import intention  # noqa: E402


class Intention(unittest.TestCase):

    def test_valeur(self):
        self.assertEqual(
            intention("Quel est le taux de chômage dans la province d'Al Hoceima ?"),
            "valeur")

    def test_classement(self):
        for question in ("Quelle province a le taux de chômage le plus élevé ?",
                         "Classe les communes par population",
                         "Quelles sont les trois premières provinces ?"):
            with self.subTest(question=question):
                self.assertEqual(intention(question), "classement")

    def test_comparaison(self):
        self.assertEqual(intention("Compare Tétouan et Larache sur la population"),
                         "comparaison")

    def test_definition(self):
        for question in ("Que mesure le taux d'urbanisation ?",
                         "D'où viennent vos chiffres ?",
                         "Comment est calculé le taux de chômage ?"):
            with self.subTest(question=question):
                self.assertEqual(intention(question), "definition")

    def test_couverture(self):
        for question in ("Que sais-tu sur la santé ?",
                         "Quelles données avez-vous sur l'éducation ?"):
            with self.subTest(question=question):
                self.assertEqual(intention(question), "couverture")

    def test_politesse_seule_est_une_conversation(self):
        for question in ("Bonjour", "Merci beaucoup !", "ok"):
            with self.subTest(question=question):
                self.assertEqual(intention(question), "conversation")

    def test_politesse_suivie_d_une_question_reste_une_question(self):
        """Le premier mot ne doit pas emporter le reste de la phrase.

        « Bonjour, je voudrais le taux de chômage » est une demande de
        valeur ; la traiter comme une salutation perdrait la question.
        """
        self.assertNotEqual(
            intention("Bonjour, je voudrais le taux de chômage à Tétouan"),
            "conversation")

    def test_comparaison_l_emporte_sur_le_classement(self):
        """L'ordre des motifs compte, et il n'est pas arbitraire.

        « Compare le taux le plus élevé de X et Y » contient un superlatif :
        essayé dans le mauvais ordre, il devient un classement et la question
        perd ses deux territoires.
        """
        self.assertEqual(
            intention("Compare le taux de chômage le plus élevé entre Tétouan "
                      "et Larache"),
            "comparaison")


if __name__ == "__main__":
    unittest.main()
