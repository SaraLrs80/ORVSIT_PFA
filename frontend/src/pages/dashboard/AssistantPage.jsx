// L'assistant conversationnel — écran de discussion.
//
// Trois partis pris d'interface, et chacun découle d'une décision prise côté
// serveur :
//
//   1. La SOURCE est affichée sous chaque réponse, séparée du texte. Elle ne
//      se lit pas comme une phrase mais comme une référence, parce qu'elle sert
//      à vérifier — et non à convaincre.
//
//   2. Un REFUS n'est pas une erreur. Il est présenté sobrement, avec son
//      motif, dans le même style qu'une réponse. Le moteur distingue six
//      motifs ; les masquer reviendrait à effacer un travail qui a coûté cher.
//
//   3. Le pouce vert ou rouge alimente message_feedback. C'est le seul canal
//      d'évaluation qui vienne de vrais usagers plutôt que d'un jeu de test
//      écrit à l'avance.
//
// L'historique est tenu par le serveur : on ne garde ici que ce qui est à
// l'écran. Un rechargement de page reprend la conversation là où elle était.

import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import {
  MessageSquare, Plus, Send, ThumbsDown, ThumbsUp, Loader2, Info,
  Pencil, Trash2, Check, X,
} from "lucide-react";
import DashboardLayout from "../../components/DashboardLayout";
import Confirmation from "../../components/Confirmation";
import {
  donnerUnAvis, lireFil, listerConversations, poserQuestion,
  renommerConversation, supprimerConversation,
} from "../../api/assistant";

// Les motifs de refus, rendus lisibles. Les clés viennent du moteur.
const MOTIF = {
  indicateur: "cette donnée n'est pas au catalogue",
  territoire: "territoire hors de la région",
  niveaux: "niveaux territoriaux différents",
  niveau_non_servi: "échelle non servie",
  hors_niveau: "non publié à ce niveau",
  millesime: "millésime indisponible",
  projection: "projection non permise",
  calcul: "calcul non permis",
  composite: "indicateur composite non permis",
  ventilation: "ventilation non publiée",
};

const SUGGESTIONS = [
  "Quel est le taux de chômage dans la province d'Al Hoceima ?",
  "Quelle province a le taux de pauvreté le plus élevé ?",
  "Que sais-tu sur la santé au niveau communal ?",
  "Compare Tétouan et Larache sur la population.",
];

export default function AssistantPage() {
  const [conversations, setConversations] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [saisie, setSaisie] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [souci, setSouci] = useState(null);
  const [avis, setAvis] = useState({});          // message_id -> true | false
  const [renomme, setRenomme] = useState(null);  // conversation_id en cours d'édition
  const [nouveauTitre, setNouveauTitre] = useState("");
  const [aSupprimer, setASupprimer] = useState(null);   // la conversation visée
  const bas = useRef(null);
  const emplacement = useLocation();

  useEffect(() => { rafraichirConversations(); }, []);

  // La pastille d'accès transmet le territoire consulté. On PRÉ-REMPLIT la
  // saisie, on ne pose pas la question : personne n'a demandé qu'on décide de
  // l'indicateur à sa place.
  useEffect(() => {
    const amorce = emplacement.state?.amorce;
    if (amorce) setSaisie((s) => s || `${amorce} `);
  }, [emplacement.state]);
  useEffect(() => {
    bas.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, enCours]);

  async function rafraichirConversations() {
    try { setConversations(await listerConversations()); } catch { /* silencieux */ }
  }

  async function ouvrir(id) {
    setConversationId(id);
    setSouci(null);
    try {
      const fil = await lireFil(id);
      setMessages(fil.map((m) => ({
        id: m.message_id,
        role: m.role,
        texte: m.contenu,
        branche: m.branche,
        refus: m.refus,
      })));
    } catch {
      setSouci("Impossible d'ouvrir cette conversation.");
    }
  }

  function nouvelle() {
    setConversationId(null);
    setMessages([]);
    setSaisie("");
    setSouci(null);
  }

  async function envoyer(texte) {
    const question = (texte ?? saisie).trim();
    if (!question || enCours) return;

    // On affiche la question tout de suite : l'attente est longue, et voir sa
    // propre question s'inscrire vaut mieux qu'un champ qui se vide sans rien.
    setMessages((m) => [...m, { id: `q${Date.now()}`, role: "user", texte: question }]);
    setSaisie("");
    setEnCours(true);
    setSouci(null);

    try {
      const r = await poserQuestion(question, conversationId);
      if (!conversationId) {
        setConversationId(r.conversation_id);
        rafraichirConversations();
      }
      setMessages((m) => [...m, {
        id: r.message_id,
        role: "assistant",
        texte: r.reponse,
        branche: r.branche,
        refus: r.refus,
        source: r.source,
        millesime: r.millesime,
        duree: r.duree_ms,
      }]);
    } catch (e) {
      setSouci(e?.response?.data?.detail || "L'assistant n'a pas répondu.");
    } finally {
      setEnCours(false);
    }
  }

  async function noter(messageId, utile) {
    setAvis((a) => ({ ...a, [messageId]: utile }));
    await donnerUnAvis(messageId, utile);
  }

  async function validerRenommage(id) {
    const titre = nouveauTitre.trim();
    setRenomme(null);
    if (!titre) return;
    try {
      await renommerConversation(id, titre);
      rafraichirConversations();
    } catch {
      setSouci("Le renommage a échoué.");
    }
  }

  // Une suppression est irréversible : on nomme ce qui va disparaître, plutôt
  // qu'un « êtes-vous sûr ? » qui ne dit rien de ce qu'on efface.
  async function effacer() {
    const id = aSupprimer?.conversation_id;
    setASupprimer(null);
    if (!id) return;
    try {
      await supprimerConversation(id);
      if (id === conversationId) nouvelle();
      rafraichirConversations();
    } catch {
      setSouci("La suppression a échoué.");
    }
  }

  return (
    <DashboardLayout title="Assistant" active="assistant">
      <div className="grid gap-5 lg:grid-cols-[240px_minmax(0,1fr)]">

        {/* ---- colonne des conversations ---- */}
        <aside className="card-orvsit p-3 h-fit hidden lg:block">
          <button onClick={nouvelle}
            className="w-full inline-flex items-center justify-center gap-2 rounded-xl
                       bg-navy text-white text-[12.5px] font-bold py-2.5
                       hover:bg-navy-2 transition-colors">
            <Plus size={14} /> Nouvelle conversation
          </button>
          <div className="mt-3 space-y-1 max-h-[62vh] overflow-y-auto defil-fin">
            {conversations.length === 0 && (
              <p className="text-[11.5px] text-t3 px-2 py-3">
                Aucune conversation pour l'instant.
              </p>
            )}
            {conversations.map((c) => renomme === c.conversation_id ? (
              <div key={c.conversation_id} className="flex items-center gap-1 px-1">
                <input
                  autoFocus
                  value={nouveauTitre}
                  onChange={(e) => setNouveauTitre(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") validerRenommage(c.conversation_id);
                    if (e.key === "Escape") setRenomme(null);
                  }}
                  maxLength={80}
                  className="flex-1 min-w-0 px-2 py-1.5 rounded-lg border border-blue
                             bg-surface text-[12px] focus:outline-none"
                />
                <button onClick={() => validerRenommage(c.conversation_id)}
                  title="Valider" className="p-1 text-teal hover:text-navy">
                  <Check size={13} />
                </button>
                <button onClick={() => setRenomme(null)}
                  title="Annuler" className="p-1 text-t3 hover:text-navy">
                  <X size={13} />
                </button>
              </div>
            ) : (
              <div key={c.conversation_id}
                className={`group flex items-center rounded-lg transition-colors ${
                  c.conversation_id === conversationId
                    ? "bg-blue-soft" : "hover:bg-bg"}`}>
                <button
                  onClick={() => ouvrir(c.conversation_id)}
                  className={`flex-1 min-w-0 text-left px-2.5 py-2 text-[12px] ${
                    c.conversation_id === conversationId
                      ? "text-navy font-semibold" : "text-t2"}`}>
                  <MessageSquare size={12} className="inline mr-1.5 -mt-0.5" />
                  {c.titre || "Sans titre"}
                </button>
                {/* Les actions n'apparaissent qu'au survol : elles ne doivent
                    pas concurrencer le titre, qui est ce qu'on vient lire. */}
                <div className="flex opacity-0 group-hover:opacity-100
                                transition-opacity pr-1">
                  <button
                    onClick={() => {
                      setRenomme(c.conversation_id);
                      setNouveauTitre(c.titre || "");
                    }}
                    title="Renommer"
                    className="p-1 text-t3 hover:text-navy">
                    <Pencil size={12} />
                  </button>
                  <button onClick={() => setASupprimer(c)}
                    title="Supprimer"
                    className="p-1 text-t3 hover:text-coral">
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* ---- le fil ---- */}
        <section className="card-orvsit p-0 flex flex-col min-h-[70vh]">
          <div className="flex-1 overflow-y-auto p-5 space-y-4 defil-fin">

            {messages.length === 0 && (
              <div className="py-8">
                <h2 className="text-lg font-extrabold text-navy">
                  Posez votre question
                </h2>
                <p className="text-[13px] text-t2 mt-1.5 max-w-xl">
                  L'assistant restitue les indicateurs officiels de la région,
                  avec leur source et leur millésime. Il ne calcule rien et ne
                  produit aucune estimation : quand une donnée n'existe pas, il
                  le dit.
                </p>
                <div className="mt-5 flex flex-wrap gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} onClick={() => envoyer(s)}
                      className="text-left text-[12px] text-t2 border border-line
                                 rounded-xl px-3 py-2 hover:border-navy-3
                                 hover:text-navy transition-colors">
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m) => m.role === "user" ? (
              <div key={m.id} className="flex justify-end">
                <div className="max-w-[80%] bg-navy text-white rounded-2xl
                                rounded-br-md px-4 py-2.5 text-[13px]">
                  {m.texte}
                </div>
              </div>
            ) : (
              <div key={m.id} className="flex justify-start">
                <div className="max-w-[85%]">
                  <div className={`rounded-2xl rounded-bl-md px-4 py-3 text-[13px]
                                   leading-relaxed ${
                    m.refus ? "bg-bg border border-line text-t2"
                            : "bg-surface border border-line text-t1"}`}>
                    {m.texte}
                  </div>

                  {/* La provenance, séparée du texte : elle sert à vérifier. */}
                  {(m.source || m.millesime) && (
                    <p className="mt-1.5 text-[10.5px] text-t3 leading-snug">
                      {m.millesime && <>Millésime {m.millesime} · </>}
                      {m.source}
                    </p>
                  )}

                  {/* Un refus n'est pas une erreur : on en donne le motif. */}
                  {m.refus && (
                    <p className="mt-1.5 text-[10.5px] text-t3 inline-flex
                                  items-center gap-1">
                      <Info size={11} />
                      {MOTIF[m.refus] || m.refus}
                    </p>
                  )}

                  {typeof m.id === "number" && (
                    <div className="mt-1.5 flex items-center gap-1">
                      <button onClick={() => noter(m.id, true)}
                        title="Cette réponse m'a été utile"
                        className={`p-1 rounded transition-colors ${
                          avis[m.id] === true ? "text-teal" : "text-t3 hover:text-navy"}`}>
                        <ThumbsUp size={12} />
                      </button>
                      <button onClick={() => noter(m.id, false)}
                        title="Cette réponse ne m'a pas aidé"
                        className={`p-1 rounded transition-colors ${
                          avis[m.id] === false ? "text-coral" : "text-t3 hover:text-navy"}`}>
                        <ThumbsDown size={12} />
                      </button>
                      {m.duree && (
                        <span className="text-[10px] text-t3 ml-1">
                          {(m.duree / 1000).toFixed(1)} s
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {enCours && (
              <div className="flex items-center gap-2 text-[12px] text-t3">
                <Loader2 size={13} className="animate-spin" />
                Recherche dans le catalogue…
              </div>
            )}
            {souci && (
              <p className="text-[12px] text-coral font-semibold">{souci}</p>
            )}
            <div ref={bas} />
          </div>

          {/* ---- la saisie ---- */}
          <form onSubmit={(e) => { e.preventDefault(); envoyer(); }}
            className="border-t border-line p-3 flex gap-2">
            <input
              value={saisie}
              onChange={(e) => setSaisie(e.target.value)}
              placeholder="Quel est le taux de chômage à Tétouan ?"
              maxLength={500}
              className="flex-1 px-4 py-2.5 rounded-xl border border-line bg-bg
                         text-[13px] focus:bg-surface focus:border-blue
                         focus:outline-none focus:ring-4 focus:ring-blue-soft
                         transition"
            />
            <button type="submit" disabled={enCours || !saisie.trim()}
              className="px-4 rounded-xl bg-navy text-white disabled:opacity-40
                         hover:bg-navy-2 transition-colors">
              <Send size={15} />
            </button>
          </form>
        </section>
      </div>

      <Confirmation
        ouvert={aSupprimer !== null}
        danger
        titre={`Supprimer « ${aSupprimer?.titre || "cette conversation"} » ?`}
        detail="Les questions et les réponses de ce fil seront effacées. Cette action ne peut pas être annulée."
        action="Supprimer"
        onConfirme={effacer}
        onFerme={() => setASupprimer(null)}
      />
    </DashboardLayout>
  );
}
