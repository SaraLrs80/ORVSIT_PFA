"""
Les gardiens du temps et de l'intention.

CE QU'ILS PROTÈGENT
Ils écartent les questions auxquelles la plateforme ne peut pas répondre sans
inventer : une projection, un millésime absent, un calcul, une tranche d'âge
non publiée. Un gardien trop laxiste laisse passer une question à laquelle on
répondra faux ; un gardien trop zélé refuse une question légitime et rend
l'assistant inutilisable.

Les tests portent donc autant sur ce qui doit être REFUSÉ que sur ce qui doit
PASSER — c'est ce second groupe qui manque le plus souvent, et c'est lui qui
protège contre le durcissement progressif des règles.
"""

import unittest

from tests import contexte  # noqa: F401
from app.assistant.gardiens import garde_intention, garde_temps


class GardeTemps(unittest.TestCase):

    def test_annee_future_refusee(self):
        refus = garde_temps("Quel sera le taux de chômage en 2030 ?")
        self.assertIsNotNone(refus)
        self.assertEqual(refus["refus"], "projection")

    def test_horizon_en_toutes_lettres_refuse(self):
        """« dans dix ans » ne contient aucun chiffre à repérer."""
        refus = garde_temps("Combien d'habitants dans dix ans ?")
        self.assertIsNotNone(refus)
        self.assertEqual(refus["refus"], "projection")

    def test_millesime_absent_refuse_en_nommant_ce_qui_existe(self):
        refus = garde_temps("La population en 2019 ?",
                            millesimes_disponibles={"2014", "2024"})
        self.assertIsNotNone(refus)
        self.assertEqual(refus["refus"], "millesime")
        self.assertIn("2014", refus["message"])
        self.assertIn("2024", refus["message"])

    def test_millesime_disponible_accepte(self):
        self.assertIsNone(garde_temps("La population en 2024 ?",
                                      millesimes_disponibles={"2024"}))

    def test_periode_couvre_les_annees_intermediaires(self):
        """Un millésime « 2014-2024 » couvre tout l'intervalle."""
        self.assertIsNone(garde_temps("Et en 2019 ?",
                                      millesimes_disponibles={"2014-2024"}))

    def test_annee_portee_par_le_libelle(self):
        """L'année scolaire du libellé compte comme millésime couvert.

        « Taux de scolarisation des 6-11 ans en 2023/2024 » porte son année
        dans son nom, quand sa colonne `annee` vaut seulement 2024. Sans
        lecture du libellé, la question qui reprend cette année scolaire est
        refusée pour un millésime qu'elle contient pourtant.
        """
        self.assertIsNone(garde_temps(
            "Le taux de scolarisation en 2023 ?",
            millesimes_disponibles={"2024"},
            libelle="Taux de scolarisation des 6-11 ans en 2023/2024"))

    def test_question_sans_annee_passe(self):
        self.assertIsNone(garde_temps("Quel est le taux de chômage ?",
                                      millesimes_disponibles={"2024"}))


class GardeIntention(unittest.TestCase):

    def test_calcul_demande_refuse(self):
        for question in ("Calcule le nombre d'habitants par médecin",
                         "Quelle est la moyenne du taux de chômage des 8 provinces ?"):
            with self.subTest(question=question):
                refus = garde_intention(question)
                self.assertIsNotNone(refus, "ce calcul aurait dû être refusé")

    def test_agregation_entre_territoires_refusee(self):
        """Agréger plusieurs territoires demande un nombre non publié."""
        for question in ("Donne la moyenne de toutes les communes",
                         "Quel est le total des populations des provinces ?",
                         "Fais la moyenne régionale du taux d'activité"):
            with self.subTest(question=question):
                self.assertIsNotNone(garde_intention(question))

    def test_moyenne_dans_le_nom_de_l_indicateur_acceptee(self):
        """« moyenne » appartient au nom de plusieurs indicateurs publiés.

        Le mot seul n'est pas le signal : « température moyenne », « humidité
        relative moyenne », « taille moyenne des ménages » sont des libellés.
        Les refuser écarterait des questions parfaitement légitimes.
        """
        for question in ("Quelle est la température moyenne à Fahs-Anjra ?",
                         "Humidité relative moyenne, province de Tétouan ?",
                         "Distance moyenne des logements à la route goudronnée ?",
                         "Taille moyenne des ménages à Ouezzane ?",
                         "Quel est le total des autoroutes en kilomètres "
                         "à Tanger-Assilah ?"):
            with self.subTest(question=question):
                self.assertIsNone(garde_intention(question),
                                  "un nom d'indicateur a été pris pour un calcul")

    def test_indice_composite_refuse(self):
        refus = garde_intention("Donne-moi un indice global de développement "
                                "par province")
        self.assertIsNotNone(refus)

    def test_question_sur_la_methode_acceptee(self):
        """« Comment est calculé X » demande une définition, pas un calcul.

        La confusion est facile et coûteuse : elle transforme une question
        légitime sur la méthode en refus pour calcul interdit.
        """
        for question in ("Comment est calculé le taux de chômage ?",
                         "Comment calcule-t-on le taux d'urbanisation ?",
                         "Sur quoi se base le taux d'analphabétisme ?"):
            with self.subTest(question=question):
                self.assertIsNone(garde_intention(question),
                                  "une question de méthode a été refusée")

    def test_tranche_age_non_publiee_refusee(self):
        refus = garde_intention("Combien de personnes de 18 à 22 ans ?",
                                ventilations_disponibles=["0-4 ans", "5-9 ans"])
        self.assertIsNotNone(refus)

    def test_tranche_age_du_libelle_acceptee(self):
        """La tranche demandée est celle de l'indicateur lui-même."""
        self.assertIsNone(garde_intention(
            "Quelle est la population de 7 à 12 ans ?",
            libelle="Population de 7 à 12 ans"))

    def test_question_ordinaire_passe(self):
        self.assertIsNone(garde_intention(
            "Quel est le taux de chômage dans la province d'Al Hoceima ?"))


if __name__ == "__main__":
    unittest.main()
