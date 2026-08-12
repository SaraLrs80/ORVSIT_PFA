"""
La recherche de l'indicateur — le point où une réponse devient fausse
sans jamais paraître fausse.

LE RISQUE PARTICULIER DE CETTE COUCHE
Une erreur de recherche ne produit pas un message d'erreur : elle produit une
valeur exacte, prise au mauvais indicateur, présentée avec la bonne source.
« Taux d'urbanisation » qui retourne le taux de chômage donne un nombre
parfaitement réel et parfaitement hors sujet. C'est la faute la plus
difficile à repérer en lisant une réponse.

Les tests lisent le catalogue réel par le faux entrepôt : ils éprouvent donc
la recherche sur les 224 indicateurs effectivement servis, sans base de
données.
"""

import unittest

from tests import contexte

contexte.brancher()

from app.assistant.moteur import _membre_demande  # noqa: E402
from app.assistant.recherche import _racine, _racines, chercher  # noqa: E402

PROVINCE = "prefecture_province"


def premier(question, niveau=PROVINCE):
    """Le nom de la famille la mieux classée pour cette question."""
    candidats = chercher(None, question, niveau)
    return candidats[0]["nom"] if candidats else None


class Racinisation(unittest.TestCase):

    def test_pluriel_et_feminin_donnent_la_meme_racine(self):
        """« privé » et « privées » désignent la même chose.

        Sans racinisation, les deux formes donnaient deux racines
        différentes et le bon indicateur perdait au profit d'une modalité
        sans rapport.
        """
        self.assertEqual(_racine("prive"), _racine("privees"))
        self.assertEqual(_racine("commune"), _racine("communes"))

    def test_troncature_ne_confond_pas_deux_mots_distincts(self):
        """« internet » et « international » ne doivent pas se confondre.

        Une racine trop courte les rendait identiques, et une question sur
        l'accès à internet ramenait la migration internationale.
        """
        self.assertNotEqual(_racine("internet"), _racine("international"))

    def test_les_chiffres_sont_conserves(self):
        """« 7 à 12 ans » et « 10 ans et plus » ne diffèrent que par eux.

        Écartés comme des mots trop brefs, ils rendaient les tranches d'âge
        indistinguables.
        """
        self.assertIn("7", _racines("Population de 7 à 12 ans"))
        self.assertIn("12", _racines("Population de 7 à 12 ans"))

    def test_les_mots_vides_sont_ecartes(self):
        racines = _racines("le taux de la population dans une commune")
        self.assertNotIn("le", racines)
        self.assertNotIn("de", racines)


class Pertinence(unittest.TestCase):

    def test_un_mot_commun_ne_suffit_pas(self):
        """« taux d'urbanisation » ne doit pas ramener « Taux de chômage ».

        Les deux libellés partagent le mot « taux », présent dans des dizaines
        de familles. Une correspondance sur ce seul mot donnerait une valeur
        exacte prise au mauvais indicateur.
        """
        nom = premier("Quel est le taux d'urbanisation ?")
        self.assertIsNotNone(nom)
        self.assertIn("urbanisation", nom.lower())

    def test_le_secteur_ne_compte_pas_comme_un_mot_de_l_indicateur(self):
        """« espérance de vie » ne doit pas ramener un indicateur du secteur
        « Conditions de vie » sur le seul mot « vie »."""
        nom = premier("Quelle est l'espérance de vie ?")
        if nom is not None:
            self.assertNotIn("température", nom.lower())

    def test_un_terme_precis_trouve_son_indicateur(self):
        for question, attendu in (
                ("Quel est le taux de chômage ?", "chômage"),
                ("Quelle est la population légale ?", "population"),
                ("Quel est le taux d'analphabétisme ?", "analphabétisme")):
            with self.subTest(question=question):
                nom = premier(question)
                self.assertIsNotNone(nom, f"aucun candidat pour « {question} »")
                self.assertIn(attendu, nom.lower())

    def test_question_hors_catalogue_ne_rend_rien(self):
        """Mieux vaut aucun candidat qu'un candidat pris par hasard."""
        self.assertIsNone(premier("Combien d'entreprises ont été créées ?"))


class ChoixDeLaVentilation(unittest.TestCase):
    """Dans une famille à plusieurs déclinaisons, laquelle la question vise ?"""

    @staticmethod
    def _famille(etiquettes):
        return {"membres": [{"indicateur_id": i, "etiquette": e}
                            for i, e in enumerate(etiquettes)]}

    def test_l_etiquette_nommee_l_emporte(self):
        """Les trois horizons migratoires ont chacun leur dénominateur.

        Prendre le premier membre d'office donnerait, pour une question sur
        cinq ans, la définition de la migration de durée de vie — un
        dénominateur différent, donc une réponse fausse.
        """
        famille = self._famille(["durée de vie", "5 ans", "10 ans"])
        self.assertEqual(
            _membre_demande(famille, "l'indice de sorties migratoires sur 5 ans"), 1)
        self.assertEqual(
            _membre_demande(famille, "l'indice de sorties migratoires sur 10 ans"), 2)

    def test_sans_etiquette_reconnue_on_garde_le_premier(self):
        """Le comportement antérieur reste intact quand rien ne distingue."""
        famille = self._famille(["durée de vie", "5 ans", "10 ans"])
        self.assertEqual(
            _membre_demande(famille, "l'indice de sorties migratoires"), 0)

    def test_famille_a_un_seul_membre(self):
        famille = self._famille([None])
        self.assertEqual(_membre_demande(famille, "peu importe"), 0)


if __name__ == "__main__":
    unittest.main()
