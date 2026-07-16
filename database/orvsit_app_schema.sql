-- =====================================================================
--  ORVSIT — Base applicative « orvsit_app »
--  Tables non analytiques : utilisateurs, demandes d'accès, assistant IA,
--  journal d'usage. Séparée du data warehouse « dwh_orvsit » (données TTA).
--
--  Moteur : PostgreSQL 13+
--
--  Mise en place :
--     createdb orvsit_app                       -- (ou via pgAdmin / init_app_db.py)
--     psql -d orvsit_app -f orvsit_app_schema.sql
--
--  Remarque : PostgreSQL ne permet pas de clé étrangère entre deux bases.
--  Les colonnes qui référencent le DWH (territoire_id, indicateur_id) sont
--  donc des « références logiques » (soft references), à valider côté
--  application, pas des FOREIGN KEY.
-- =====================================================================

-- ------------------------------------------------------------------
-- 1. Types énumérés
-- ------------------------------------------------------------------
DROP TYPE IF EXISTS role_utilisateur  CASCADE;
DROP TYPE IF EXISTS statut_compte     CASCADE;
DROP TYPE IF EXISTS statut_demande    CASCADE;
DROP TYPE IF EXISTS role_message      CASCADE;

CREATE TYPE role_utilisateur AS ENUM
    ('administrateur', 'analyste', 'decideur', 'partenaire', 'chercheur');

CREATE TYPE statut_compte AS ENUM
    ('actif', 'inactif', 'suspendu');

CREATE TYPE statut_demande AS ENUM
    ('en_attente', 'approuvee', 'rejetee');

CREATE TYPE role_message AS ENUM
    ('user', 'assistant', 'system');

-- ------------------------------------------------------------------
-- 2. Utilisateurs
-- ------------------------------------------------------------------
DROP TABLE IF EXISTS utilisateur CASCADE;
CREATE TABLE utilisateur (
    utilisateur_id      BIGSERIAL       PRIMARY KEY,
    nom_complet         VARCHAR(160)    NOT NULL,
    email               VARCHAR(190)    NOT NULL UNIQUE,
    mot_de_passe_hash   VARCHAR(255)    NOT NULL,          -- bcrypt / argon2, jamais en clair
    role                role_utilisateur NOT NULL DEFAULT 'analyste',
    organisation        VARCHAR(160),
    statut              statut_compte   NOT NULL DEFAULT 'actif',
    date_creation       TIMESTAMPTZ     NOT NULL DEFAULT now(),
    derniere_connexion  TIMESTAMPTZ
);

COMMENT ON TABLE  utilisateur IS 'Comptes de la plateforme ORVSIT (analystes, décideurs, admins, partenaires).';
COMMENT ON COLUMN utilisateur.mot_de_passe_hash IS 'Empreinte du mot de passe (bcrypt/argon2). Ne jamais stocker en clair.';

-- ------------------------------------------------------------------
-- 3. Demandes d'accès (formulaire public → validation admin)
-- ------------------------------------------------------------------
DROP TABLE IF EXISTS demande_acces CASCADE;
CREATE TABLE demande_acces (
    demande_id          BIGSERIAL       PRIMARY KEY,
    nom_complet         VARCHAR(160)    NOT NULL,
    email               VARCHAR(190)    NOT NULL,
    organisation        VARCHAR(160),
    profil_souhaite     role_utilisateur NOT NULL DEFAULT 'analyste',
    motif               TEXT,
    statut              statut_demande  NOT NULL DEFAULT 'en_attente',
    date_demande        TIMESTAMPTZ     NOT NULL DEFAULT now(),
    traite_par          BIGINT          REFERENCES utilisateur(utilisateur_id) ON DELETE SET NULL,
    date_traitement     TIMESTAMPTZ,
    utilisateur_cree    BIGINT          REFERENCES utilisateur(utilisateur_id) ON DELETE SET NULL
);

COMMENT ON TABLE demande_acces IS 'Demandes d''accès reçues via la landing page ; l''admin approuve (crée un utilisateur) ou rejette.';

-- ------------------------------------------------------------------
-- 4. Assistant IA — conversations & messages
-- ------------------------------------------------------------------
DROP TABLE IF EXISTS conversation CASCADE;
CREATE TABLE conversation (
    conversation_id     BIGSERIAL       PRIMARY KEY,
    utilisateur_id      BIGINT          NOT NULL REFERENCES utilisateur(utilisateur_id) ON DELETE CASCADE,
    titre               VARCHAR(200),
    date_creation       TIMESTAMPTZ     NOT NULL DEFAULT now(),
    date_maj            TIMESTAMPTZ     NOT NULL DEFAULT now()
);

DROP TABLE IF EXISTS message CASCADE;
CREATE TABLE message (
    message_id          BIGSERIAL       PRIMARY KEY,
    conversation_id     BIGINT          NOT NULL REFERENCES conversation(conversation_id) ON DELETE CASCADE,
    role                role_message    NOT NULL,          -- user | assistant | system
    contenu             TEXT            NOT NULL,
    modele              VARCHAR(80),                       -- ex : 'gpt-4o-mini', 'llama-3', règle interne...
    tokens              INT,
    date_envoi          TIMESTAMPTZ     NOT NULL DEFAULT now()
);

COMMENT ON TABLE conversation IS 'Fil de discussion entre un utilisateur et l''assistant IA.';
COMMENT ON TABLE message      IS 'Messages d''une conversation (question utilisateur / réponse assistant).';

-- Références logiques d'une réponse de l'assistant vers le DWH
-- (quels territoires / indicateurs ont servi à répondre). Pas de FK inter-bases.
DROP TABLE IF EXISTS message_reference CASCADE;
CREATE TABLE message_reference (
    reference_id        BIGSERIAL       PRIMARY KEY,
    message_id          BIGINT          NOT NULL REFERENCES message(message_id) ON DELETE CASCADE,
    type_entite         VARCHAR(20)     NOT NULL,          -- 'territoire' | 'indicateur'
    entite_id           BIGINT          NOT NULL,          -- territoire_id / indicateur_id dans dwh_orvsit (soft ref)
    libelle             VARCHAR(200)
);

COMMENT ON TABLE message_reference IS 'Traçabilité : entités du DWH (territoire/indicateur) citées par une réponse IA. Référence logique, pas de FK inter-bases.';

-- Retour utilisateur sur une réponse (pouce haut/bas)
DROP TABLE IF EXISTS message_feedback CASCADE;
CREATE TABLE message_feedback (
    feedback_id         BIGSERIAL       PRIMARY KEY,
    message_id          BIGINT          NOT NULL REFERENCES message(message_id) ON DELETE CASCADE,
    utilisateur_id      BIGINT          REFERENCES utilisateur(utilisateur_id) ON DELETE SET NULL,
    utile               BOOLEAN,
    commentaire         TEXT,
    date_feedback       TIMESTAMPTZ     NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------
-- 5. Journal d'usage (supervision par l'administrateur)
-- ------------------------------------------------------------------
DROP TABLE IF EXISTS journal_usage CASCADE;
CREATE TABLE journal_usage (
    evenement_id        BIGSERIAL       PRIMARY KEY,
    utilisateur_id      BIGINT          REFERENCES utilisateur(utilisateur_id) ON DELETE SET NULL,
    action              VARCHAR(80)     NOT NULL,          -- 'connexion','export','consultation_fiche','question_ia'...
    cible               VARCHAR(160),                      -- ex : 'fiche:ouezzane', 'indicateur:eau'
    details             JSONB,
    date_evenement      TIMESTAMPTZ     NOT NULL DEFAULT now()
);

COMMENT ON TABLE journal_usage IS 'Trace des actions (connexions, exports, questions IA…) pour la supervision de l''usage.';

-- ------------------------------------------------------------------
-- 6. Index
-- ------------------------------------------------------------------
CREATE INDEX idx_conversation_utilisateur ON conversation(utilisateur_id);
CREATE INDEX idx_message_conversation     ON message(conversation_id);
CREATE INDEX idx_message_reference_msg    ON message_reference(message_id);
CREATE INDEX idx_feedback_message         ON message_feedback(message_id);
CREATE INDEX idx_demande_statut           ON demande_acces(statut);
CREATE INDEX idx_journal_utilisateur      ON journal_usage(utilisateur_id);
CREATE INDEX idx_journal_date             ON journal_usage(date_evenement);

-- ------------------------------------------------------------------
-- 7. Trigger : mettre à jour conversation.date_maj à chaque message
-- ------------------------------------------------------------------
CREATE OR REPLACE FUNCTION maj_date_conversation() RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversation SET date_maj = now() WHERE conversation_id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_maj_conversation ON message;
CREATE TRIGGER trg_maj_conversation
    AFTER INSERT ON message
    FOR EACH ROW EXECUTE FUNCTION maj_date_conversation();

-- ------------------------------------------------------------------
-- 8. Jeu de départ minimal
--    Le hash ci-dessous est un EXEMPLE bcrypt pour le mot de passe
--    « changeme » — à REMPLACER après le premier déploiement.
-- ------------------------------------------------------------------
INSERT INTO utilisateur (nom_complet, email, mot_de_passe_hash, role, organisation, statut)
VALUES ('Administrateur ORVSIT', 'admin@crtta.ma',
        '$2b$12$abcdefghijklmnopqrstuuWZ2b1oJ5F0Vd0m6l6l2m0m2m0m2m0m2', -- EXEMPLE à remplacer
        'administrateur', 'CRTTA', 'actif')
ON CONFLICT (email) DO NOTHING;

-- Exemple de demandes d'accès en attente (pour tester l'écran admin)
INSERT INTO demande_acces (nom_complet, email, organisation, profil_souhaite, motif) VALUES
 ('Yasmine El Fassi', 'y.elfassi@ouezzane.ma', 'Commune de Ouezzane', 'decideur',
  'Suivre les indicateurs sociaux de la province pour le plan d''action communal.'),
 ('Omar Ziani', 'o.ziani@uae.ac.ma', 'Université Abdelmalek Essaâdi', 'chercheur',
  'Étude sur les disparités urbain/rural dans la région TTA.');

-- =====================================================================
--  FIN DU SCHÉMA orvsit_app
-- =====================================================================
