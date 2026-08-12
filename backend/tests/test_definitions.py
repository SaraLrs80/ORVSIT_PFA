"""
Le jugement porté sur une définition du catalogue.

POURQUOI CETTE FONCTION MÉRITE DES TESTS
La colonne `definition` du catalogue ne contient pas toujours une définition :
selon les lignes, une véritable explication, une note de provenance, ou le nom
brut de la colonne d'origine. `_definition_redigee` tranche au moment de
répondre — mieux vaut annoncer qu'aucune définition n'est rédigée que servir
un identifiant technique en guise d'explication.

Cette fonction est aussi le SEUL juge de la question : la mesure de complétude
du catalogue s'en sert également. Deux critères pour une même question
finiraient par produire deux réponses différentes.
"""

import unittest

from tests import contexte

contexte.brancher()

from app.assistant.moteur import _definition_redigee  # noqa: E402


class DefinitionRedigee(unittest.TestCase):

    def test_identifiant_technique_refuse(self):
        """Un nom de colonne n'est pas une phrase."""
        for texte in ("population_sedentaire_5ans_plus", "temp_moyenne"):
            with self.subTest(texte=texte):
                self.assertIsNone(_definition_redigee(texte, "Population sédentaire"))

    def test_note_de_provenance_refusee(self):
        """La provenance n'explique pas ce que l'indicateur mesure."""
        self.assertIsNone(_definition_redigee(
            "Taux de chômage (%). Thème : socio_economic.",
            "Taux de chômage"))

    def test_repetition_du_libelle_refusee(self):
        """Une définition qui répète le libellé n'apprend rien."""
        self.assertIsNone(_definition_redigee(
            "Population légale. Niveaux commune et province, 2024.",
            "Population légale"))

    def test_definition_veritable_acceptee(self):
        texte = ("Part des chômeurs dans la population active de 15 ans et "
                 "plus. Le dénominateur est la population active et non la "
                 "population totale.")
        self.assertIsNotNone(_definition_redigee(texte, "Taux de chômage"))

    def test_la_tracabilite_est_ecartee_du_texte_rendu(self):
        """La mention de traçabilité ne doit pas être lue à l'utilisateur.

        Elle documente la vérification faite au chargement ; elle n'a rien à
        faire dans une réponse en français.
        """
        rendu = _definition_redigee(
            "Part de la population résidant en milieu urbain, rapportée à la "
            "population totale du territoire. "
            "[Traçabilité : vérifié, 441/441 valeurs concordantes.]",
            "Taux d'urbanisation")
        self.assertIsNotNone(rendu)
        self.assertNotIn("Traçabilité", rendu)

    def test_definition_vide_ou_absente(self):
        self.assertIsNone(_definition_redigee(None, "Peu importe"))
        self.assertIsNone(_definition_redigee("", "Peu importe"))

    def test_le_libelle_n_a_pas_besoin_d_etre_contigu(self):
        """La soustraction se fait mot à mot, et non d'un seul tenant.

        « Taux de pauvreté (incidence H). Niveaux commune et province, 2024 »
        ne contient pas son libellé d'affilée : la mention des niveaux
        s'intercale. Une comparaison de chaînes le jugerait informatif.
        """
        self.assertIsNone(_definition_redigee(
            "Taux de pauvreté (incidence H). Niveaux commune et province, 2024.",
            "Taux de pauvreté"))


if __name__ == "__main__":
    unittest.main()
