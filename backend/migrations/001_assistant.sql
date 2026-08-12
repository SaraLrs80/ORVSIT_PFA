-- ---------------------------------------------------------------------------
-- La trace du moteur, ajoutée aux tables existantes de l'assistant.
-- Base : orvsit_app.  À exécuter une fois, dans pgAdmin ou psql.
--
-- CE QUI EXISTAIT DÉJÀ, ET QU'ON GARDE
--   conversation       conversation_id, utilisateur_id, titre, dates
--   message            role (user / assistant / system), contenu, modele,
--                      tokens, date_envoi
--   message_reference  ce que la réponse cite : indicateur, territoire
--   message_feedback   l'avis de l'utilisateur sur une réponse
--
-- Ce schéma est meilleur que celui que j'avais écrit avant de regarder :
--   - une seule table `message` pour les questions ET les réponses, comme un
--     vrai fil de discussion ;
--   - `message_reference` porte la traçabilité de façon normalisée, au lieu de
--     colonnes recopiées ;
--   - `message_feedback` ouvre un canal d'évaluation par de vrais usagers.
--
-- CE QU'IL MANQUAIT
--   La trace du moteur : par quelle branche la réponse est sortie, pour quel
--   motif elle a été refusée, et si la reformulation du modèle a été retenue
--   ou rejetée au profit du brouillon déterministe.
--
--   Leur place est dans `message`, à côté de `modele` et `tokens` qui sont
--   déjà des métadonnées de génération de même nature.
--
-- CE QU'ON N'AJOUTE PAS, ET POURQUOI
--   Aucune colonne d'état dans `conversation`. Le dernier territoire et le
--   dernier indicateur se lisent dans les `message_reference` du dernier
--   message de l'assistant. Les recopier créerait deux vérités qui finiraient
--   par se contredire.
--
-- Tout est additif : un DROP COLUMN suffirait à revenir en arrière.
-- ---------------------------------------------------------------------------

ALTER TABLE message ADD COLUMN IF NOT EXISTS branche       VARCHAR(20);
ALTER TABLE message ADD COLUMN IF NOT EXISTS refus         VARCHAR(30);
ALTER TABLE message ADD COLUMN IF NOT EXISTS reformulation VARCHAR(80);
ALTER TABLE message ADD COLUMN IF NOT EXISTS duree_ms      INTEGER;

COMMENT ON COLUMN message.branche IS
    'Par quelle branche du moteur la réponse est sortie : valeur, classement, '
    'comparaison, definition, couverture, refus, question, conversation.';
COMMENT ON COLUMN message.refus IS
    'Motif du refus, quand il y en a un : indicateur, territoire, projection, '
    'millesime, calcul, composite, ventilation, hors_niveau.';
COMMENT ON COLUMN message.reformulation IS
    'Sort de la reformulation par le modèle : « acceptée », ou « rejetée — '
    'chiffre inventé : 7.5 ». Une réponse rejetée n''est jamais servie : c''est '
    'le brouillon déterministe qui l''est.';

-- Retrouver rapidement les réponses d'une branche donnée, pour l'analyse.
CREATE INDEX IF NOT EXISTS message_branche_idx
    ON message (branche, date_envoi DESC);
