// Page d'accueil : ce que la plateforme contient.
//
// POURQUOI PAS UNE CARTE D'IDENTITÉ RÉGIONALE
// La monographie interactive publiée sur orvsit.crtta.ma présente déjà la
// région — population, superficie, urbanisation, PIB, portrait territorial,
// atouts structurants — et la Fiche territoriale couvre la lecture par
// territoire. Une troisième présentation des mêmes chiffres n'aurait rien
// appris à personne.
//
// Le diagnostic a confirmé qu'il fallait y renoncer : sur 234 indicateurs
// publiés, 159 seulement portent une valeur régionale, et la Santé n'en
// compte qu'un sur vingt-quatre. Une carte régionale aurait été bavarde en
// démographie et muette en santé.
//
// Cette page dit ce que ni le site public ni les autres écrans ne disent :
// l'état du catalogue. Combien d'indicateurs, dans quels secteurs, à quelles
// échelles, de quels millésimes et de quelles sources. Rien n'est calculé :
// on compte des lignes.
//
// La part d'indicateurs portant une définition rédigée n'y figure pas. C'est
// une mesure de complétude interne, utile à qui tient le catalogue et sans
// intérêt pour qui consulte : un écran d'accueil n'expose pas ce qui reste à
// faire.

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Layers, MapPin, CalendarDays, Landmark,
  FileText, ArrowLeftRight, Compass, MessageSquare, ArrowRight,
} from "lucide-react";
import DashboardLayout from "../../components/DashboardLayout";
import Reveal from "../../components/Reveal";
import { getApercu } from "../../api/dashboard";

const nombre = (n) => Number(n).toLocaleString("fr-FR");

// Les quatre écrans de consultation, dans l'ordre où on les découvre :
// un territoire, puis deux, puis un thème, puis la question libre.
const ENTREES = [
  { to: "/dashboard/fiche", Icon: FileText, titre: "Fiche territoriale",
    texte: "Tous les indicateurs d'une province ou d'une commune, carte comprise." },
  { to: "/dashboard/comparer", Icon: ArrowLeftRight, titre: "Comparer",
    texte: "Plusieurs territoires du même niveau, sur les mêmes indicateurs." },
  { to: "/dashboard/explorer", Icon: Compass, titre: "Explorer",
    texte: "Un secteur à la fois, sur l'ensemble de la région." },
  { to: "/dashboard/assistant", Icon: MessageSquare, titre: "Assistant",
    texte: "Poser la question en français ; la réponse cite sa source." },
];

export default function VueEnsemblePage() {
  const [data, setData] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    getApercu()
      .then(setData)
      .catch(() => setErreur("Impossible de charger l'état du catalogue."))
      .finally(() => setChargement(false));
  }, []);

  const cat = data?.catalogue;
  const terr = data?.territoires;
  // L'échelle des barres : le secteur le plus fourni occupe toute la largeur.
  const maxSecteur = cat ? Math.max(...cat.secteurs.map((s) => s.total)) : 1;

  return (
    <DashboardLayout title="Vue d'ensemble" active="overview">
      {chargement ? (
        <p className="text-t2">Chargement…</p>
      ) : erreur ? (
        <p className="text-coral">{erreur}</p>
      ) : (
        <>
          <div className="mb-7">
            <h1 className="text-3xl font-extrabold text-navy">
              Le catalogue de la plateforme
            </h1>
            <p className="text-t2 mt-1.5 max-w-3xl leading-relaxed">
              Chaque écran de cette plateforme lit le même catalogue
              d'indicateurs officiels. Voici son état : ce qu'il couvre, à
              quelles échelles, et d'où viennent les chiffres.
            </p>
          </div>

          {/* Quatre décomptes, pas quatre indices. */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-7">
            <Chiffre i={0} Icon={Layers} boite="bg-blue-soft text-blue"
              valeur={nombre(cat.total)} label="indicateurs servis"
              note={`${cat.secteurs.length} secteurs`} />
            <Chiffre i={1} Icon={MapPin} boite="bg-gold-soft text-gold"
              valeur={nombre(terr.provinces + terr.communes)} label="territoires servis"
              note={`${terr.provinces} préfectures et provinces · ${terr.communes} communes`} />
            <Chiffre i={2} Icon={CalendarDays} boite="bg-teal-soft text-teal"
              valeur={data.millesimes[0]?.annee ?? "—"} label="millésime principal"
              note={`${nombre(data.millesimes[0]?.n ?? 0)} indicateurs sur ${nombre(cat.total)}`} />
            <Chiffre i={3} Icon={Landmark} boite="bg-coral-soft text-coral"
              valeur={data.sources.length} label="organismes producteurs"
              note="aucune donnée sans source" />
          </div>

          <div className="grid lg:grid-cols-3 gap-6">
            {/* La couverture, secteur par secteur */}
            <div className="lg:col-span-2 card-orvsit p-5">
              <h2 className="font-bold text-navy">Couverture par secteur</h2>
              <p className="text-xs text-t3 mt-1 mb-5">
                Un indicateur peut être publié à l'échelle provinciale, communale,
                ou aux deux. Les colonnes ne s'additionnent donc pas.
              </p>

              <div className="grid grid-cols-[1fr_auto] gap-x-4 text-[11px] font-bold
                              text-t3 uppercase tracking-wide mb-2">
                <span>Secteur</span>
                <span className="tabular-nums">Total · Prov. · Comm.</span>
              </div>

              <div className="space-y-3.5">
                {cat.secteurs.map((s) => (
                  <div key={s.secteur}>
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="font-semibold text-navy text-sm">
                        {s.secteur}
                      </span>
                      <span className="text-sm text-t2 tabular-nums shrink-0">
                        <b className="text-navy">{s.total}</b>
                        <span className="text-t3"> · </span>{s.province}
                        <span className="text-t3"> · </span>{s.commune}
                      </span>
                    </div>
                    {/* La barre entière = le total servi ; la part foncée =
                        ce qui descend jusqu'à la commune. */}
                    <div className="mt-1.5 h-2 rounded-full bg-bg overflow-hidden">
                      <div className="h-full rounded-full bg-blue-soft"
                           style={{ width: `${(s.total / maxSecteur) * 100}%` }}>
                        <div className="h-full rounded-full bg-navy"
                             style={{ width: `${(s.commune / s.total) * 100}%` }} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex flex-wrap gap-4 mt-5 text-xs text-t2">
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-navy" /> disponible au niveau communal
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-blue-soft" /> niveau provincial seulement
                </span>
              </div>
            </div>

            {/* Millésimes et sources */}
            <div className="flex flex-col gap-6">
              <div className="card-orvsit p-5">
                <h2 className="font-bold text-navy">Millésimes</h2>
                <p className="text-xs text-t3 mt-1 mb-4">
                  Un millésime peut couvrir une période — évolution intercensitaire
                  ou année scolaire.
                </p>
                <div className="space-y-2">
                  {data.millesimes.map((m) => (
                    <div key={m.annee} className="flex items-center gap-3">
                      <span className="w-24 shrink-0 font-semibold text-navy text-sm
                                       tabular-nums">
                        {m.annee}
                      </span>
                      <div className="flex-1 h-2 rounded-full bg-bg overflow-hidden">
                        <div className="h-full rounded-full bg-gold"
                             style={{ width: `${(m.n / cat.total) * 100}%` }} />
                      </div>
                      <span className="w-8 text-right text-sm text-t2 tabular-nums">
                        {m.n}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card-orvsit p-5 flex-1">
                <h2 className="font-bold text-navy">Sources</h2>
                <p className="text-xs text-t3 mt-1 mb-4">
                  Organisme producteur, tel qu'il est cité sur chaque indicateur.
                </p>
                <div className="space-y-2.5">
                  {data.sources.map((s) => (
                    <div key={s.organisme}
                         className="flex items-baseline justify-between gap-3">
                      <span className="text-sm text-t2 leading-snug">{s.organisme}</span>
                      <span className="text-sm font-bold text-navy tabular-nums shrink-0">
                        {s.n}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Par où commencer */}
          <h2 className="font-bold text-navy mt-8 mb-3">Par où commencer</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {ENTREES.map(({ to, Icon, titre, texte }, i) => (
              <Reveal key={to} delay={i * 80} className="h-full">
                <button
                  onClick={() => navigate(to)}
                  className="group h-full w-full text-left card-orvsit survolable p-5
                             cursor-pointer">
                  <span className="w-11 h-11 rounded-xl bg-navy text-white
                                   flex items-center justify-center mb-3">
                    <Icon size={20} />
                  </span>
                  <div className="flex items-center gap-1.5 font-bold text-navy">
                    {titre}
                    <ArrowRight size={15}
                      className="opacity-0 -translate-x-1 transition-all
                                 group-hover:opacity-100 group-hover:translate-x-0" />
                  </div>
                  <p className="text-xs text-t2 mt-1.5 leading-relaxed">{texte}</p>
                </button>
              </Reveal>
            ))}
          </div>

          <p className="text-xs text-t3 mt-7 leading-relaxed max-w-3xl">
            Ces nombres sont des décomptes du catalogue, vérifiables ligne à ligne
            dans <code className="text-t2">referential.dim_indicateur</code>. Aucune
            valeur n'y est agrégée ni recalculée. Pour le portrait de la région
            elle-même — superficie, PIB, atouts structurants — se reporter à la
            monographie interactive de l'ORVSIT.
          </p>
        </>
      )}
    </DashboardLayout>
  );
}

function Chiffre({ i, Icon, boite, valeur, label, note }) {
  return (
    <Reveal delay={i * 90} className="h-full">
      <div className="h-full card-orvsit p-5">
        <div className={`w-11 h-11 rounded-xl flex items-center justify-center mb-3 ${boite}`}>
          <Icon size={21} />
        </div>
        <div className="text-2xl font-extrabold text-navy tabular-nums">{valeur}</div>
        <div className="text-xs text-t2 mt-1">{label}</div>
        {note && <div className="text-[11px] text-t3 mt-1.5 leading-snug">{note}</div>}
      </div>
    </Reveal>
  );
}
