# Provenance — `sante_capacite_province.csv`

## Source
**« La Santé en chiffres 2024 »** — Ministère de la Santé et de la Protection
Sociale du Royaume du Maroc (annuaire statistique, données 2024).
Fichier source archivé : `Sante en chiffre 2024 VF.pdf`.

## Données extraites (région Tanger-Tétouan-Al Hoceïma, par province/préfecture)

| Colonne du CSV | Tableau source du PDF | Détail |
|---|---|---|
| `essp` | **Tableau 31** — Répartition des ESSP par région, province/préfecture, milieu et catégorie | colonne « Total ESSP » (établissements de soins de santé primaires) |
| `hopitaux` | **Tableau 32** — Répartition des hôpitaux par région, province/préfecture et catégorie | colonne « Total établissements hospitaliers » |
| `medecins_public` | **Tableau 37** — Répartition des médecins du secteur public par région, province/préfecture et réseau | somme des totaux par réseau (RH + REESP + REMS) |
| `paramedical_public` | **Tableau 40** — Répartition du personnel infirmier et de technicien de santé du secteur public | somme des totaux par réseau (RH + RESSP + REMS) |

## Indicateurs dérivés (taux per-capita)
Calculés dans `calcul_idt.py`, en rapportant chaque comptage à la **population
légale** de la province (RGPH 2024, `dim_indicateur.indicateur_id = 40`) :

- `Médecins pour 10 000 habitants`  = medecins_public / population × 10 000
- `Personnel paramédical pour 10 000 habitants` = paramedical_public / population × 10 000
- `ESSP pour 100 000 habitants` = essp / population × 100 000

## Pourquoi cette extraction
Les comptages santé disponibles initialement dans l'entrepôt étaient **partiels**
à l'échelle provinciale (plusieurs provinces sans capacité litière renseignée).
Ils ont donc été **complétés** par les données officielles complètes ci-dessus,
puis transformées en **taux comparables** (per-capita) pour alimenter la dimension
« Santé » de l'Indice de Développement Territorial (IDT).
