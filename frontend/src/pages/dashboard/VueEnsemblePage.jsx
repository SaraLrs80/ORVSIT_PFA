// Vue d'ensemble régionale : synthèse des disparités de la région TTA.
// KPIs + classement des territoires (par IDT ou par dimension) + zones prioritaires.

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Users, Gauge, ArrowLeftRight, AlertTriangle } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import DashboardLayout from "../../components/DashboardLayout";
import Reveal from "../../components/Reveal";
import { getApercu } from "../../api/dashboard";

// Métriques que l'on peut afficher dans le classement.
const METRIQUES = [
  { key: "idt", label: "Indice global (IDT)" },
  { key: "score_education", label: "Éducation" },
  { key: "score_conditions_vie", label: "Conditions de vie" },
  { key: "score_sante", label: "Santé" },
  { key: "score_emploi", label: "Emploi" },
  { key: "score_numerique", label: "Numérique" },
  { key: "score_accessibilite", label: "Accessibilité" },
];

// Couleur de la barre selon le niveau (seuils de la maquette).
function couleurBarre(v) {
  if (v >= 60) return "bg-teal";
  if (v >= 45) return "bg-gold";
  return "bg-red-500";
}

const fmtNum = (n) => Number(n).toLocaleString("fr-FR");
const fmtM = (n) => (n / 1_000_000).toFixed(2).replace(".", ",") + " M";

export default function VueEnsemblePage() {
  const [data, setData] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState("");
  const [metrique, setMetrique] = useState("idt");
  const navigate = useNavigate();

  useEffect(() => {
    getApercu()
      .then(setData)
      .catch(() => setErreur("Impossible de charger la vue d'ensemble."))
      .finally(() => setChargement(false));
  }, []);

  return (
    <DashboardLayout title="Vue d'ensemble régionale" active="overview">
      {chargement ? (
        <p className="text-t2">Chargement…</p>
      ) : erreur ? (
        <p className="text-red-600">{erreur}</p>
      ) : (
        <>
          {/* En-tête */}
          <div className="mb-6">
            <h1 className="text-3xl font-extrabold text-navy">Vue d'ensemble régionale</h1>
            <p className="text-t2 mt-1">
              Synthèse des disparités territoriales de la région Tanger-Tétouan-Al Hoceïma
            </p>
          </div>

          {/* Cartes KPI */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <KpiCard i={0} Icon={Users} boite="bg-gold-soft text-gold-2"
              valeur={fmtM(data.population_regionale)} label="Population régionale" />
            <KpiCard i={1} Icon={Gauge} boite="bg-blue-soft text-blue"
              valeur={`${data.idt_moyen} /100`} label="IDT moyen région" />
            <KpiCard i={2} Icon={ArrowLeftRight} boite="bg-coral-soft text-coral"
              valeur={`${data.ecart_max} pts`} label="Écart territorial max." />
            <KpiCard i={3} Icon={AlertTriangle} boite="bg-red-50 text-red-600"
              valeur={data.nb_zones_prioritaires} label="Zones prioritaires" />
          </div>

          <div className="grid lg:grid-cols-3 gap-6">
            {/* Colonne de gauche : classement + principales disparités */}
            <div className="lg:col-span-2 space-y-6">
            {/* Classement des territoires */}
            <div className="bg-surface border border-line rounded-2xl p-5">
              <div className="flex items-center justify-between mb-5">
                <h2 className="font-bold text-navy">Classement des territoires</h2>
                <select
                  value={metrique}
                  onChange={(e) => setMetrique(e.target.value)}
                  className="text-sm border border-line rounded-xl px-3 py-2 bg-bg text-navy font-semibold focus:outline-none focus:border-blue"
                >
                  {METRIQUES.map((m) => (
                    <option key={m.key} value={m.key}>{m.label}</option>
                  ))}
                </select>
              </div>

              <p className="text-xs text-t3 mb-3">
                Score = position relative dans la région (100 = le plus fort des 8, 0 = le plus faible).
                Cliquez sur un territoire pour voir le détail dans sa fiche.
              </p>
              <div className="space-y-1">
                {[...data.classement]
                  .sort((a, b) => b[metrique] - a[metrique])
                  .map((t, i) => (
                    <button
                      key={t.territoire_id}
                      onClick={() => navigate(`/dashboard/fiche/${t.territoire_id}`)}
                      className="w-full flex items-center gap-3 rounded-xl px-2 py-2 -mx-2 hover:bg-bg transition-colors text-left cursor-pointer"
                    >
                      <div className="w-6 h-6 rounded-full bg-bg text-t2 text-xs font-bold flex items-center justify-center shrink-0">
                        {i + 1}
                      </div>
                      <div className="w-36 shrink-0 font-semibold text-navy text-sm truncate">
                        {t.nom}
                      </div>
                      <div className="flex-1 h-2.5 rounded-full bg-bg overflow-hidden">
                        <div
                          className={`h-full rounded-full ${couleurBarre(t[metrique])}`}
                          style={{ width: `${t[metrique]}%` }}
                        />
                      </div>
                      <div className="w-10 text-right font-bold text-navy text-sm">
                        {t[metrique]}
                      </div>
                    </button>
                  ))}
              </div>

              {/* Légende des seuils */}
              <div className="flex gap-4 mt-5 text-xs text-t2">
                <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-teal" /> Élevé (≥ 60)</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-gold" /> Moyen (45-59)</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-red-500" /> Faible (&lt; 45)</span>
              </div>
            </div>

            {/* Principales disparités */}
            <div className="bg-surface border border-line rounded-2xl p-5">
              <h2 className="font-bold text-navy mb-1">Principales disparités</h2>
              <p className="text-xs text-t3 mb-4">écarts clés entre territoires</p>
              <div className="space-y-3">
                {data.disparites.map((d) => (
                  <div
                    key={d.indicateur}
                    className="flex items-center justify-between gap-3 border-b border-line last:border-0 pb-3 last:pb-0"
                  >
                    <div className="min-w-0">
                      <div className="font-semibold text-navy text-sm">{d.indicateur}</div>
                      <div className="text-xs text-t3 truncate">
                        {d.max_nom} {d.max_val}
                        {d.unite} · {d.min_nom} {d.min_val}
                        {d.unite}
                      </div>
                    </div>
                    <div className="text-coral font-bold text-sm shrink-0">
                      {d.ecart}
                      {d.unite === "%" ? " pts" : ""}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            </div>

            {/* Colonne de droite : répartition urbain/rural + zones prioritaires */}
            <div className="flex flex-col gap-6">
            {/* Donut urbain / rural */}
            <div className="bg-surface border border-line rounded-2xl p-5">
              <h2 className="font-bold text-navy mb-1">Répartition urbain / rural</h2>
              <p className="text-xs text-t3 mb-2">population régionale</p>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={[
                      { name: "Urbain", value: data.urbain_rural.urbain },
                      { name: "Rural", value: data.urbain_rural.rural },
                    ]}
                    dataKey="value"
                    innerRadius={48}
                    outerRadius={72}
                    paddingAngle={2}
                    startAngle={90}
                    endAngle={-270}
                  >
                    <Cell fill="#0a2540" />
                    <Cell fill="#f5a623" />
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="flex justify-around text-center">
                <div>
                  <div className="flex items-center gap-1.5 text-xs text-t2">
                    <span className="w-2.5 h-2.5 rounded-full bg-navy" /> Urbain
                  </div>
                  <div className="text-lg font-extrabold text-navy">{data.urbain_rural.urbain} %</div>
                </div>
                <div>
                  <div className="flex items-center gap-1.5 text-xs text-t2">
                    <span className="w-2.5 h-2.5 rounded-full bg-gold" /> Rural
                  </div>
                  <div className="text-lg font-extrabold text-navy">{data.urbain_rural.rural} %</div>
                </div>
              </div>
            </div>

            {/* Zones prioritaires */}
            <div className="bg-surface border border-line rounded-2xl p-5 flex-1">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle size={18} className="text-red-600" />
                <h2 className="font-bold text-navy">Zones prioritaires</h2>
              </div>
              <p className="text-sm text-t2 mb-4">
                Territoires dont l'IDT est faible (&lt; 45) — à cibler en priorité.
              </p>
              {data.zones_prioritaires.length === 0 ? (
                <p className="text-sm text-t2">Aucune zone sous le seuil.</p>
              ) : (
                <div className="space-y-2">
                  {data.zones_prioritaires.map((nom) => {
                    const t = data.classement.find((x) => x.nom === nom);
                    return (
                      <div key={nom} className="flex items-center justify-between rounded-xl bg-red-50 border border-red-100 px-4 py-2.5">
                        <span className="font-semibold text-navy text-sm">{nom}</span>
                        <span className="text-red-600 font-bold text-sm">{t?.idt}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
            </div>
          </div>

          <p className="text-xs text-t3 mt-6">
            Données réelles (RGPH 2024, Ministère de la Santé) — IDT calculé sur 6 dimensions :
            éducation, conditions de vie, santé, emploi, numérique, accessibilité.
          </p>
        </>
      )}
    </DashboardLayout>
  );
}

// Petite carte KPI (avec animation d'apparition)
function KpiCard({ i, Icon, boite, valeur, label }) {
  return (
    <Reveal delay={i * 90} className="h-full">
      <div className="h-full bg-surface border border-line rounded-2xl p-5 shadow-[0_6px_22px_rgba(16,37,66,0.06)] hover:shadow-[0_12px_34px_rgba(16,37,66,0.12)] hover:-translate-y-1 transition-all duration-300">
        <div className={`w-11 h-11 rounded-xl flex items-center justify-center mb-3 ${boite}`}>
          <Icon size={22} />
        </div>
        <div className="text-2xl font-extrabold text-navy">{valeur}</div>
        <div className="text-xs text-t2 mt-1">{label}</div>
      </div>
    </Reveal>
  );
}
