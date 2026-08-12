// Barre d'export, reprise de celle du site officiel.
//
// Elle ne connaît rien aux données : la page lui fournit une fonction qui,
// au moment du clic, construit colonnes et lignes. La construction est donc
// toujours faite sur l'état courant de l'écran — filtres, niveau et sélection
// compris — et non sur un instantané figé au premier rendu.
//
// Les lignes contiennent des NOMBRES, pas des chaînes déjà mises en forme :
// c'est ce qui permet au CSV d'écrire « 12,3 » pendant que le classeur Excel
// garde un vrai nombre, sur lequel on peut trier et sommer.
//
// Les formats sont ajoutés un par un ; ce fichier grandira avec eux.

import { useState } from "react";
import { FileSpreadsheet, FileText, Image, FileDown, Printer } from "lucide-react";
import { telechargerCSV, telechargerXLSX, nomDeFichier } from "../utils/export";
import { exporterCartePNG, exporterCartePDF } from "../utils/exportCarte";
import { imprimer } from "../utils/impression";
import { signaler } from "../api/journal";

/**
 * Props :
 *   - nom     : nom de fichier, sans extension ni date
 *   - donnees : () => ({ colonnes, lignes, entete, feuilles? })
 *               `feuilles` est optionnel : [{ nom, colonnes, lignes }].
 *               S'il est fourni, le classeur Excel comporte un onglet par
 *               entrée ; sinon il reprend colonnes et lignes en une feuille.
 *   - carte   : () => ({ noeud, titre, sousTitre, palette, bornes, note,
 *               source, attribution })
 *   - formats : quels boutons afficher. Les exports d'image ne saisissent que
 *               la carte : leur place est au-dessus d'elle, pas dans l'en-tête
 *               de la page où ils laisseraient croire qu'ils capturent l'écran
 *               entier. D'où la possibilité de scinder la barre en deux.
 *   - compact : version réduite, pour se poser dans un bandeau
 */
export default function BarreExport({
  nom, donnees, carte, formats = ["csv", "xlsx"], compact = false,
  titreImpression = null,
}) {
  const [enCours, setEnCours] = useState(null);
  const [souci, setSouci] = useState(null);

  async function exporter(format) {
    setSouci(null);

    if (format === "imprimer") {
      setEnCours(format);
      try {
        await imprimer({ carte, titre: titreImpression || nom });
        signaler("impression", nom);   // après le succès seulement
      } catch (e) {
        setSouci(`Impression impossible : ${e?.message || e}`);
      } finally {
        setEnCours(null);
      }
      return;
    }

    if (format === "png" || format === "pdf") {
      const c = carte?.();
      if (!c?.carteLeaflet) {
        setSouci("La carte doit être affichée pour être exportée.");
        setTimeout(() => setSouci(null), 4000);
        return;
      }
      setEnCours(format);
      try {
        const options = { ...c, nomFichier: `${nomDeFichier(nom)}_carte` };
        if (format === "png") await exporterCartePNG(options);
        else await exporterCartePDF(options);
        signaler("export", `${format} · ${nom}`);
      } catch (e) {
        const m = String(e?.message || "");
        setSouci(/jspdf/i.test(m)
          ? "Module PDF absent — lancez « npm install jspdf »."
          : `Export impossible : ${m || e}`);
      } finally {
        setEnCours(null);
      }
      return;
    }

    const d = donnees() || {};
    if (!d.colonnes?.length || !d.lignes?.length) {
      setSouci("Rien à exporter avec les filtres actuels.");
      setTimeout(() => setSouci(null), 4000);
      return;
    }
    setEnCours(format);
    try {
      if (format === "csv") {
        telechargerCSV(nomDeFichier(nom), d.colonnes, d.lignes, d.entete);
      } else if (format === "xlsx") {
        const feuilles = d.feuilles?.length
          ? d.feuilles
          : [{ nom: "Données", colonnes: d.colonnes, lignes: d.lignes }];
        await telechargerXLSX(nomDeFichier(nom), feuilles, d.entete);
      }
      signaler("export", `${format} · ${nom}`);
    } catch (e) {
      // Le cas le plus probable : la bibliothèque xlsx n'est pas installée.
      // Un bouton qui ne fait rien sans dire pourquoi est pire qu'un bouton
      // absent — on affiche donc la raison.
      setSouci(/xlsx/i.test(String(e?.message))
        ? "Module Excel absent — lancez « npm install xlsx » puis rechargez."
        : `Export impossible : ${e?.message || e}`);
    } finally {
      setEnCours(null);
    }
  }

  const CATALOGUE = {
    png: { libelle: "PNG", Icone: Image,
           titre: "Image de la carte seule, avec son titre, sa légende et sa source" },
    pdf: { libelle: "PDF", Icone: FileDown,
           titre: "La même carte déposée dans une page A4, prête à imprimer" },
    csv: { libelle: "CSV", Icone: FileText,
           titre: "Valeurs séparées par des points-virgules" },
    xlsx: { libelle: "Excel", Icone: FileSpreadsheet,
            titre: "Classeur .xlsx, un onglet par secteur" },
    imprimer: { libelle: "Imprimer", Icone: Printer,
                titre: "Mise en page A4 — la boîte d'impression permet aussi d'enregistrer en PDF" },
  };
  const IMAGE = new Set(["png", "pdf"]);
  const boutons = formats.filter((f) => CATALOGUE[f] && (!IMAGE.has(f) || carte));

  const taille = compact
    ? "px-2.5 py-1.5 text-[11px] rounded-[9px]"
    : "px-3 py-2 text-[11.5px] rounded-[10px]";

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex gap-1.5">
        {boutons.map((cle) => {
          const { libelle, Icone, titre } = CATALOGUE[cle];
          return (
            <button key={cle} type="button" title={titre}
              onClick={() => exporter(cle)} disabled={enCours !== null}
              className={`inline-flex items-center gap-1.5 bg-white border border-line
                          font-extrabold text-t2 transition-colors hover:text-navy
                          hover:border-navy-3 disabled:opacity-50 ${taille}`}>
              <Icone size={compact ? 12 : 13} />
              {enCours === cle ? "…" : libelle}
            </button>
          );
        })}
      </div>
      {souci && (
        <span className="text-[10.5px] text-coral font-semibold max-w-[280px] text-right">
          {souci}
        </span>
      )}
    </div>
  );
}
