// Espace administrateur — supervision d'usage.
// 4 compteurs + un graphe de l'usage des 7 derniers jours (recharts).

import { useEffect, useState } from "react";
import { LogIn, Users, FileDown, MessageSquare } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import DashboardLayout from "../../components/DashboardLayout";
import Reveal from "../../components/Reveal";
import { getStatistiques } from "../../api/admin";

export default function SupervisionPage() {
  const [stats, setStats] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState("");

  useEffect(() => {
    getStatistiques()
      .then(setStats)
      .catch(() => setErreur("Impossible de charger les statistiques."))
      .finally(() => setChargement(false));
  }, []);

  // Cartes construites une fois les stats chargées
  const cartes = stats
    ? [
        { label: "Connexions (30 j)", valeur: stats.connexions_30j, Icon: LogIn, boite: "bg-blue-soft text-blue" },
        { label: "Utilisateurs actifs", valeur: stats.utilisateurs_actifs, Icon: Users, boite: "bg-gold-soft text-gold-2" },
        { label: "Rapports exportés", valeur: stats.rapports_exportes, Icon: FileDown, boite: "bg-teal-soft text-teal" },
        { label: "Questions à l'IA", valeur: stats.questions_ia, Icon: MessageSquare, boite: "bg-coral-soft text-coral" },
      ]
    : [];

  return (
    <DashboardLayout title="Supervision" active="supervision">
      <p className="text-t2 text-sm mb-6">
        Suivi de l'usage de la plateforme (connexions, exports, questions à l'assistant IA).
      </p>

      {chargement ? (
        <p className="text-t2">Chargement…</p>
      ) : erreur ? (
        <p className="text-red-600">{erreur}</p>
      ) : (
        <>
          {/* Cartes de compteurs (apparition en cascade + soulèvement au survol) */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {cartes.map((c, i) => (
              <Reveal key={c.label} delay={i * 90} className="h-full">
                <div className="h-full bg-surface border border-line rounded-2xl p-5 shadow-[0_6px_22px_rgba(16,37,66,0.06)] hover:shadow-[0_12px_34px_rgba(16,37,66,0.12)] hover:-translate-y-1 transition-all duration-300">
                  <div className={`w-11 h-11 rounded-xl flex items-center justify-center mb-3 ${c.boite}`}>
                    <c.Icon size={22} />
                  </div>
                  <div className="text-3xl font-extrabold text-navy">{c.valeur}</div>
                  <div className="text-xs text-t2 mt-1">{c.label}</div>
                </div>
              </Reveal>
            ))}
          </div>

          {/* Graphe usage hebdomadaire */}
          <div className="bg-surface border border-line rounded-2xl p-5">
            <h2 className="font-bold text-navy mb-4">Usage hebdomadaire</h2>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={stats.usage_hebdo}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e9edf3" />
                <XAxis dataKey="jour" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis tickLine={false} axisLine={false} fontSize={12} allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Bar dataKey="connexions" name="Connexions" fill="#0a2540" radius={[4, 4, 0, 0]} />
                <Bar dataKey="exports" name="Exports" fill="#f5a623" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </DashboardLayout>
  );
}
