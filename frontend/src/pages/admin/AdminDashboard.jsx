// Espace administrateur — gestion des demandes d'accès.
// Affichage en CARTES (fidèle à la maquette) : avatar, infos, badge profil,
// encadré du motif, boutons Approuver / Rejeter. Avec stats et filtre.

import { useEffect, useState } from "react";
import { Clock, CheckCircle2, XCircle, Inbox, Check, Mail, BadgeCheck } from "lucide-react";
import DashboardLayout from "../../components/DashboardLayout";
import Reveal from "../../components/Reveal";
import { listerDemandes, approuverDemande, rejeterDemande } from "../../api/admin";

const STATUT_STYLE = {
  en_attente: "bg-gold-soft text-gold-2",
  approuvee: "bg-teal-soft text-teal",
  rejetee: "bg-red-50 text-red-600",
};
const STATUT_LABEL = {
  en_attente: "En attente",
  approuvee: "Approuvée",
  rejetee: "Rejetée",
};

// Libellé lisible du profil demandé. Les valeurs héritées sont conservées pour
// que les demandes déposées avant la réduction à deux rôles restent lisibles.
const PROFIL_LABEL = {
  utilisateur: "Utilisateur",
  analyste: "Analyste ORVSIT",
  decideur: "Décideur régional",
  partenaire: "Partenaire institutionnel",
  chercheur: "Chercheur / universitaire",
  administrateur: "Administrateur",
};

// Couleurs d'avatar (variées, choisies selon l'id de la demande)
const AVATAR_COULEURS = [
  "bg-violet-soft text-violet",
  "bg-blue-soft text-blue",
  "bg-teal-soft text-teal",
  "bg-coral-soft text-coral",
  "bg-gold-soft text-gold-2",
];

const FILTRES = [
  { key: "toutes", label: "Toutes" },
  { key: "en_attente", label: "En attente" },
  { key: "approuvee", label: "Approuvées" },
  { key: "rejetee", label: "Rejetées" },
];

// Initiales d'un nom (ex: "Yasmine El Fassi" -> "YE")
function initiales(nom) {
  return nom
    .split(" ")
    .map((m) => m[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export default function AdminDashboard() {
  const [demandes, setDemandes] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState("");
  const [message, setMessage] = useState("");
  const [actionEnCours, setActionEnCours] = useState(null);
  const [filtre, setFiltre] = useState("toutes");

  async function charger() {
    setChargement(true);
    setErreur("");
    try {
      const data = await listerDemandes();
      setDemandes(data);
    } catch {
      setErreur("Impossible de charger les demandes.");
    } finally {
      setChargement(false);
    }
  }

  useEffect(() => {
    charger();
  }, []);

  async function handleApprouver(id) {
    setActionEnCours(id);
    setMessage("");
    try {
      const res = await approuverDemande(id);
      setMessage(`Demande approuvée : invitation envoyée à ${res.email}.`);
      await charger();
    } catch {
      setMessage("Erreur lors de l'approbation.");
    } finally {
      setActionEnCours(null);
    }
  }

  async function handleRejeter(id) {
    setActionEnCours(id);
    setMessage("");
    try {
      await rejeterDemande(id);
      setMessage("Demande rejetée.");
      await charger();
    } catch {
      setMessage("Erreur lors du rejet.");
    } finally {
      setActionEnCours(null);
    }
  }

  // Statistiques (calculées depuis la liste, sans appel supplémentaire).
  const compter = (s) => demandes.filter((d) => d.statut === s).length;
  const enAttente = compter("en_attente");
  const stats = [
    { label: "En attente", valeur: enAttente, Icon: Clock, boite: "bg-gold-soft text-gold-2" },
    { label: "Approuvées", valeur: compter("approuvee"), Icon: CheckCircle2, boite: "bg-teal-soft text-teal" },
    { label: "Rejetées", valeur: compter("rejetee"), Icon: XCircle, boite: "bg-red-50 text-red-600" },
    { label: "Total", valeur: demandes.length, Icon: Inbox, boite: "bg-blue-soft text-blue" },
  ];

  const demandesAffichees =
    filtre === "toutes" ? demandes : demandes.filter((d) => d.statut === filtre);

  return (
    <DashboardLayout title="Demandes d'accès" active="demandes">
      <p className="text-t2 text-sm mb-6">
        Approuvez ou rejetez les demandes reçues via le formulaire public.
      </p>

      {/* Cartes de statistiques */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {stats.map((s) => (
          <div
            key={s.label}
            className="bg-surface border border-line rounded-2xl p-4 flex items-center gap-3 hover:shadow-[0_8px_24px_rgba(16,37,66,0.08)] transition-shadow"
          >
            <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${s.boite}`}>
              <s.Icon size={22} />
            </div>
            <div>
              <div className="text-2xl font-extrabold text-navy">{s.valeur}</div>
              <div className="text-xs text-t2">{s.label}</div>
            </div>
          </div>
        ))}
      </div>

      {message && (
        <div className="mb-4 rounded-xl bg-blue-soft border border-blue/20 text-navy text-sm px-4 py-3">
          {message}
        </div>
      )}

      {/* En-tête de section */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-bold text-navy">Demandes d'accès</h2>
          {enAttente > 0 && (
            <span className="bg-red-500 text-white text-xs font-bold rounded-full min-w-5 h-5 px-1.5 flex items-center justify-center">
              {enAttente}
            </span>
          )}
        </div>
        <span className="text-xs text-t3">reçues via le formulaire public</span>
      </div>

      {/* Filtre */}
      <div className="flex flex-wrap gap-2 mb-5">
        {FILTRES.map((f) => {
          const actif = filtre === f.key;
          return (
            <button
              key={f.key}
              onClick={() => setFiltre(f.key)}
              className={`px-4 py-2 rounded-full text-sm font-semibold transition-colors ${
                actif
                  ? "bg-navy text-white"
                  : "bg-surface border border-line text-t2 hover:text-navy hover:border-navy/40"
              }`}
            >
              {f.label}
            </button>
          );
        })}
      </div>

      {/* Contenu : chargement / erreur / vide / cartes */}
      {chargement ? (
        <p className="text-t2">Chargement…</p>
      ) : erreur ? (
        <p className="text-red-600">{erreur}</p>
      ) : demandesAffichees.length === 0 ? (
        <p className="text-t2">Aucune demande dans cette catégorie.</p>
      ) : (
        <div className="space-y-3">
          {demandesAffichees.map((d, i) => (
            <Reveal key={d.demande_id} delay={i * 60}>
              <div className="flex items-start gap-4 p-5 rounded-2xl border border-line bg-surface hover:shadow-[0_10px_30px_rgba(16,37,66,0.08)] transition-shadow">
                {/* Avatar avec initiales */}
                <div
                  className={`w-11 h-11 rounded-xl flex items-center justify-center font-bold text-sm shrink-0 ${
                    AVATAR_COULEURS[d.demande_id % AVATAR_COULEURS.length]
                  }`}
                >
                  {initiales(d.nom_complet)}
                </div>

                {/* Infos */}
                <div className="flex-1 min-w-0">
                  <div className="font-bold text-navy">{d.nom_complet}</div>
                  <div className="flex items-center gap-1.5 text-sm text-t2 mt-0.5">
                    <Mail size={14} className="shrink-0" />
                    <span className="truncate">{d.email}</span>
                    {d.organisation && (
                      <span className="text-t3 truncate">· {d.organisation}</span>
                    )}
                  </div>
                  <div className="mt-2">
                    <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-gold-2 bg-gold-soft px-2.5 py-1 rounded-lg">
                      <BadgeCheck size={13} />
                      {PROFIL_LABEL[d.profil_souhaite] || d.profil_souhaite}
                    </span>
                  </div>
                  {d.motif && (
                    <div className="mt-3 text-sm text-t2 bg-bg border border-line rounded-xl px-4 py-2.5">
                      {d.motif}
                    </div>
                  )}
                </div>

                {/* Actions ou statut */}
                <div className="flex flex-col gap-2 shrink-0 w-32">
                  {d.statut === "en_attente" ? (
                    <>
                      <button
                        onClick={() => handleApprouver(d.demande_id)}
                        disabled={actionEnCours === d.demande_id}
                        className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-teal text-white text-sm font-semibold hover:brightness-95 transition disabled:opacity-50"
                      >
                        <Check size={15} /> Approuver
                      </button>
                      <button
                        onClick={() => handleRejeter(d.demande_id)}
                        disabled={actionEnCours === d.demande_id}
                        className="px-4 py-2 rounded-xl border border-line text-t2 text-sm font-semibold hover:border-navy hover:text-navy transition disabled:opacity-50"
                      >
                        Rejeter
                      </button>
                    </>
                  ) : (
                    <span
                      className={`inline-block text-center px-3 py-1.5 rounded-full text-xs font-semibold ${STATUT_STYLE[d.statut]}`}
                    >
                      {STATUT_LABEL[d.statut]}
                    </span>
                  )}
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      )}
    </DashboardLayout>
  );
}
