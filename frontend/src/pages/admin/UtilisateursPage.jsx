// Espace administrateur — gestion des comptes utilisateurs.
// Tableau des comptes + fenêtre « Gérer » pour changer le rôle et le statut.

import { useEffect, useState } from "react";
import { X, Plus } from "lucide-react";
import DashboardLayout from "../../components/DashboardLayout";
import {
  listerUtilisateurs,
  modifierUtilisateur,
  ajouterUtilisateur,
  supprimerUtilisateur,
} from "../../api/admin";

const ROLE_LABEL = {
  administrateur: "Administrateur",
  analyste: "Analyste ORVSIT",
  decideur: "Décideur régional",
  partenaire: "Partenaire institutionnel",
  chercheur: "Chercheur / universitaire",
};

const STATUT_STYLE = {
  actif: "bg-teal-soft text-teal",
  inactif: "bg-gold-soft text-gold-2",
  suspendu: "bg-red-50 text-red-600",
};

const ROLES = ["analyste", "decideur", "partenaire", "chercheur", "administrateur"];
const STATUTS = ["actif", "inactif", "suspendu"];

const champClasses =
  "w-full px-4 py-2.5 rounded-xl border border-line bg-bg focus:bg-surface focus:border-blue focus:outline-none focus:ring-4 focus:ring-blue-soft transition";

// Dernière connexion en texte relatif lisible (Aujourd'hui / Hier / Il y a N jours…)
function formaterConnexion(iso) {
  if (!iso) return "Jamais";
  const jours = Math.floor((Date.now() - new Date(iso)) / 86400000);
  if (jours <= 0) return "Aujourd'hui";
  if (jours === 1) return "Hier";
  if (jours < 7) return `Il y a ${jours} jours`;
  return new Date(iso).toLocaleDateString("fr-FR");
}

// Date + heure exactes (ex: 20 juil. 2026 à 14:32)
function dateExacte(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function initiales(nom) {
  return nom.split(" ").map((m) => m[0]).slice(0, 2).join("").toUpperCase();
}

export default function UtilisateursPage() {
  const [users, setUsers] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState("");
  const [message, setMessage] = useState("");

  // Utilisateur en cours de gestion (null = fenêtre fermée)
  const [gestion, setGestion] = useState(null);
  const [roleEdit, setRoleEdit] = useState("");
  const [statutEdit, setStatutEdit] = useState("");
  const [enreg, setEnreg] = useState(false);
  const [confirmSuppr, setConfirmSuppr] = useState(false); // demande de confirmation
  const [supprEnCours, setSupprEnCours] = useState(false);

  // Fenêtre de création d'un nouveau compte
  const [creation, setCreation] = useState(false);
  const [nomC, setNomC] = useState("");
  const [emailC, setEmailC] = useState("");
  const [roleC, setRoleC] = useState("analyste");
  const [orgC, setOrgC] = useState("");
  const [creEnCours, setCreEnCours] = useState(false);
  const [erreurC, setErreurC] = useState("");

  async function charger() {
    setChargement(true);
    setErreur("");
    try {
      setUsers(await listerUtilisateurs());
    } catch {
      setErreur("Impossible de charger les utilisateurs.");
    } finally {
      setChargement(false);
    }
  }

  useEffect(() => {
    charger();
  }, []);

  // Ouvre la fenêtre de gestion en pré-remplissant avec les valeurs actuelles.
  function ouvrirGestion(u) {
    setGestion(u);
    setRoleEdit(u.role);
    setStatutEdit(u.statut);
    setConfirmSuppr(false);
    setMessage("");
  }

  async function handleSupprimer() {
    setSupprEnCours(true);
    try {
      await supprimerUtilisateur(gestion.utilisateur_id);
      setMessage(`Compte de ${gestion.nom_complet} supprimé.`);
      setGestion(null);
      await charger();
    } catch (err) {
      // 400 si l'admin tente de supprimer son propre compte
      setMessage(err?.response?.data?.detail || "Erreur lors de la suppression.");
      setGestion(null);
    } finally {
      setSupprEnCours(false);
      setConfirmSuppr(false);
    }
  }

  async function enregistrer() {
    setEnreg(true);
    try {
      await modifierUtilisateur(gestion.utilisateur_id, {
        role: roleEdit,
        statut: statutEdit,
      });
      setMessage(`Compte de ${gestion.nom_complet} mis à jour.`);
      setGestion(null);
      await charger();
    } catch {
      setMessage("Erreur lors de la mise à jour.");
    } finally {
      setEnreg(false);
    }
  }

  // Ouvre la fenêtre de création (formulaire vide).
  function ouvrirCreation() {
    setNomC("");
    setEmailC("");
    setRoleC("analyste");
    setOrgC("");
    setErreurC("");
    setCreation(true);
  }

  async function creerCompte(e) {
    e.preventDefault();
    setErreurC("");
    setCreEnCours(true);
    try {
      await ajouterUtilisateur({
        nom_complet: nomC,
        email: emailC,
        role: roleC,
        organisation: orgC || null,
      });
      setMessage(`Compte créé : invitation envoyée à ${emailC}.`);
      setCreation(false);
      await charger();
    } catch (err) {
      // 400 = email déjà utilisé (message renvoyé par le backend)
      setErreurC(
        err?.response?.data?.detail || "Erreur lors de la création du compte."
      );
    } finally {
      setCreEnCours(false);
    }
  }

  return (
    <DashboardLayout title="Utilisateurs" active="utilisateurs">
      <p className="text-t2 text-sm mb-6">
        Gérez les comptes de la plateforme : rôle et statut.
      </p>

      {message && (
        <div className="mb-4 rounded-xl bg-blue-soft border border-blue/20 text-navy text-sm px-4 py-3">
          {message}
        </div>
      )}

      {chargement ? (
        <p className="text-t2">Chargement…</p>
      ) : erreur ? (
        <p className="text-red-600">{erreur}</p>
      ) : (
        <div className="rounded-2xl border border-line bg-surface overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-line">
            <div className="flex items-center gap-3">
              <h2 className="font-bold text-navy">Comptes utilisateurs</h2>
              <span className="text-xs text-t3">{users.length} compte(s)</span>
            </div>
            <button
              onClick={ouvrirCreation}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-navy text-white text-sm font-semibold hover:bg-navy-2 transition"
            >
              <Plus size={16} /> Nouveau compte
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-bg text-left text-t2 text-xs uppercase tracking-wide">
                  <th className="px-5 py-3 font-semibold">Utilisateur</th>
                  <th className="px-5 py-3 font-semibold">Rôle</th>
                  <th className="px-5 py-3 font-semibold">Dernière connexion</th>
                  <th className="px-5 py-3 font-semibold">Statut</th>
                  <th className="px-5 py-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr
                    key={u.utilisateur_id}
                    className="border-t border-line hover:bg-bg/60 transition-colors"
                  >
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-lg bg-blue-soft text-blue flex items-center justify-center text-xs font-bold shrink-0">
                          {initiales(u.nom_complet)}
                        </div>
                        <div>
                          <div className="font-semibold text-navy">{u.nom_complet}</div>
                          <div className="text-t3 text-xs">{u.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-4 text-t2">{ROLE_LABEL[u.role] || u.role}</td>
                    <td className="px-5 py-4 whitespace-nowrap">
                      <div className="text-t2">{formaterConnexion(u.derniere_connexion)}</div>
                      {u.derniere_connexion && (
                        <div className="text-t3 text-xs">
                          {dateExacte(u.derniere_connexion)}
                        </div>
                      )}
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-block px-2.5 py-1 rounded-full text-xs font-semibold ${STATUT_STYLE[u.statut]}`}
                      >
                        {u.statut}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right">
                      <button
                        onClick={() => ouvrirGestion(u)}
                        className="px-4 py-1.5 rounded-lg border border-line text-navy text-xs font-semibold hover:border-navy transition-colors"
                      >
                        Gérer
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Fenêtre « Gérer » */}
      {gestion && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-navy/40 backdrop-blur-sm"
          onClick={() => setGestion(null)}
        >
          <div
            className="w-full max-w-sm bg-surface rounded-2xl shadow-2xl p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-1">
              <h2 className="text-lg font-extrabold text-navy">Gérer le compte</h2>
              <button
                onClick={() => setGestion(null)}
                className="text-t3 hover:text-navy transition-colors"
              >
                <X size={20} />
              </button>
            </div>
            <p className="text-sm text-t2 mb-5">{gestion.nom_complet} — {gestion.email}</p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-t2 mb-1.5">Rôle</label>
                <select
                  value={roleEdit}
                  onChange={(e) => setRoleEdit(e.target.value)}
                  className={champClasses}
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {ROLE_LABEL[r]}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-t2 mb-1.5">Statut</label>
                <select
                  value={statutEdit}
                  onChange={(e) => setStatutEdit(e.target.value)}
                  className={champClasses}
                >
                  {STATUTS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setGestion(null)}
                className="flex-1 py-2.5 rounded-xl border border-line text-t2 font-semibold hover:border-navy hover:text-navy transition"
              >
                Annuler
              </button>
              <button
                onClick={enregistrer}
                disabled={enreg}
                className="flex-1 py-2.5 rounded-xl bg-navy text-white font-semibold hover:bg-navy-2 transition disabled:opacity-60"
              >
                {enreg ? "Enregistrement…" : "Enregistrer"}
              </button>
            </div>

            {/* Zone de suppression (confirmation en deux temps) */}
            <div className="mt-4 pt-4 border-t border-line">
              {!confirmSuppr ? (
                <button
                  onClick={() => setConfirmSuppr(true)}
                  className="text-sm font-semibold text-red-600 hover:underline"
                >
                  Supprimer ce compte
                </button>
              ) : (
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-red-600">Confirmer la suppression ?</span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setConfirmSuppr(false)}
                      className="px-3 py-1.5 rounded-lg border border-line text-t2 text-sm font-semibold"
                    >
                      Non
                    </button>
                    <button
                      onClick={handleSupprimer}
                      disabled={supprEnCours}
                      className="px-3 py-1.5 rounded-lg bg-red-500 text-white text-sm font-semibold hover:brightness-95 disabled:opacity-60"
                    >
                      {supprEnCours ? "Suppression…" : "Oui, supprimer"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Fenêtre « Nouveau compte » */}
      {creation && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-navy/40 backdrop-blur-sm"
          onClick={() => setCreation(false)}
        >
          <div
            className="w-full max-w-md bg-surface rounded-2xl shadow-2xl p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-1">
              <h2 className="text-lg font-extrabold text-navy">Nouveau compte</h2>
              <button
                onClick={() => setCreation(false)}
                className="text-t3 hover:text-navy transition-colors"
              >
                <X size={20} />
              </button>
            </div>
            <p className="text-sm text-t2 mb-5">
              Le compte est créé, et un e-mail d'invitation est envoyé pour définir
              le mot de passe.
            </p>

            <form onSubmit={creerCompte} className="space-y-4">
              {erreurC && (
                <div className="rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3">
                  {erreurC}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-t2 mb-1.5">
                  Nom complet
                </label>
                <input
                  value={nomC}
                  onChange={(e) => setNomC(e.target.value)}
                  required
                  placeholder="Prénom Nom"
                  className={champClasses}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-t2 mb-1.5">
                  Adresse e-mail
                </label>
                <input
                  type="email"
                  value={emailC}
                  onChange={(e) => setEmailC(e.target.value)}
                  required
                  placeholder="nom@organisation.ma"
                  className={champClasses}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-t2 mb-1.5">Rôle</label>
                <select
                  value={roleC}
                  onChange={(e) => setRoleC(e.target.value)}
                  className={champClasses}
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {ROLE_LABEL[r]}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-t2 mb-1.5">
                  Organisation (facultatif)
                </label>
                <input
                  value={orgC}
                  onChange={(e) => setOrgC(e.target.value)}
                  placeholder="Conseil régional, commune, université…"
                  className={champClasses}
                />
              </div>

              <div className="flex gap-3 pt-1">
                <button
                  type="button"
                  onClick={() => setCreation(false)}
                  className="flex-1 py-2.5 rounded-xl border border-line text-t2 font-semibold hover:border-navy hover:text-navy transition"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={creEnCours}
                  className="flex-1 py-2.5 rounded-xl bg-navy text-white font-semibold hover:bg-navy-2 transition disabled:opacity-60"
                >
                  {creEnCours ? "Création…" : "Créer le compte"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
