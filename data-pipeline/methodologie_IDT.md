# Méthodologie de calcul — Indice de Développement Territorial (IDT)
_Niveau : préfecture/province (8 territoires de la région TTA). Script : `calcul_idt.py`._

## 1. Objectif
Résumer, en **un seul score de 0 à 100 par territoire**, sa situation de
développement relative aux autres territoires de la région, pour repérer
rapidement les zones les plus en difficulté (aide à la décision).

## 2. Indicateurs retenus (tous en TAUX, présents pour les 8 provinces)

**Dimension Éducation** (4)
- Taux de scolarisation 6-11 ans (%) — sens **+** (plus haut = mieux)
- Taux d'analphabétisme 10 ans et + (%) — sens **−**
- Part « aucun niveau d'études » (%) — sens **−**
- Part « niveau supérieur » (%) — sens **+**

**Dimension Conditions de vie & services** (4)
- Accès au réseau public d'eau (%) — **+**
- Accès au réseau public d'électricité (%) — **+**
- Accès au réseau public d'assainissement (%) — **+**
- Part d'habitat précaire / bidonville (%) — **−**

**Dimension Santé** (3, densités per-capita — voir §4)
- Médecins pour 10 000 habitants — **+**
- Personnel paramédical pour 10 000 habitants — **+**
- Établissements de soins primaires (ESSP) pour 100 000 habitants — **+**

> Un indice composite se construit avec un petit nombre d'indicateurs **comparables** (en taux, pas en comptage) et à **direction claire** (l'IDH de l'ONU en utilise 4). Les ~250 autres indicateurs alimentent les écrans d'exploration, de fiche et de comparaison.

## 3. Calcul de l'IDT (3 étapes)

### Étape A — Normalisation Min-Max (chaque indicateur ramené sur 0-100)
Pour un indicateur donné, sur les 8 territoires :

    note = ( valeur − minimum ) / ( maximum − minimum ) × 100

- Si l'indicateur est **positif** : on garde `note`.
- Si l'indicateur est **négatif** (analphabétisme, habitat précaire) : on inverse →
  `note = 100 − note`.

**Exemple (accès à l'eau, indicateur positif) :** min = 87,3 (Fahs-Anjra),
max = 95,4 (M'diq). Pour Tétouan (94,5) : (94,5 − 87,3)/(95,4 − 87,3)×100 ≈ **89**.

**Exemple (analphabétisme, indicateur négatif) :** le territoire le plus alphabétisé
obtient 100, le plus analphabète 0 (grâce à l'inversion).

### Étape B — Score par dimension
Chaque dimension = **moyenne** des notes (0-100) de ses indicateurs :

    score_education      = moyenne(4 notes d'éducation)
    score_conditions_vie = moyenne(4 notes de conditions de vie)
    score_sante          = moyenne(3 notes de santé)

> On moyenne **par dimension** pour que les dimensions à plus d'indicateurs
> n'écrasent pas les autres.

### Étape C — IDT
    IDT = moyenne( score_education , score_conditions_vie , score_sante )

## 4. Densités santé (transformer des comptages en taux)
Les données santé sont des **comptages** (médecins, paramédicaux, ESSP), non
comparables tels quels. On les rapporte à la **population légale** (RGPH 2024) :

    taux = ( comptage / population ) × base

- Médecins pour 10 000 hab   = médecins / population × 10 000
- Paramédical pour 10 000 hab = paramédical / population × 10 000
- ESSP pour 100 000 hab       = ESSP / population × 100 000

Source des comptages : « Santé en chiffres 2024 » (Ministère de la Santé),
tableaux 31 (ESSP), 32 (hôpitaux), 37 (médecins), 40 (paramédical).
Voir `sante_capacite_province_SOURCE.md`.

## 5. Indicateurs de synthèse de la Vue d'ensemble
- **Population régionale** = 4 030 222 (total RGPH 2024).
- **IDT moyen** = moyenne des 8 IDT.
- **Écart territorial max.** = IDT le plus haut − IDT le plus bas.
- **Zones prioritaires** = territoires dont IDT < 45 (seuil « faible »).

## 6. Répartition urbain / rural (donut)
À partir de la population urbaine et rurale de chaque province (RGPH) :

    part_urbain = Σ(population urbaine) / Σ(population totale) × 100
    part_rural  = 100 − part_urbain

## 7. Principales disparités
Pour quelques indicateurs clés (eau, analphabétisme, assainissement,
médecins/10k), on identifie le territoire **le mieux doté** et **le moins doté**,
et l'**écart** entre eux :

    écart = valeur_max − valeur_min

Les indicateurs sont ensuite triés par écart décroissant (les plus grandes
disparités en premier).

## 8. Limites assumées (perspectives)
- Indice **relatif à la région** (0-100 = position vs les autres territoires TTA),
  pas une note absolue.
- Niveau province (8) : le niveau commune est visé comme perspective (données
  santé/infrastructure incomplètes à ce grain).
- Pas de **suivi pluriannuel** de l'IDT : les indicateurs sont issus du RGPH 2024
  (une seule année) ; une courbe d'évolution nécessiterait plusieurs millésimes.
- Méthode Min-Max (transparente) plutôt qu'ACP : l'ACP conviendrait au niveau
  commune/douar (des centaines d'observations), pas à 8 territoires.
