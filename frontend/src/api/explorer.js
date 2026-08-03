// Appels liés à l'exploration d'un thème.
//
// Trois fonctions qui reflètent les trois endpoints. Ce fichier ne décide rien :
// il traduit une URL en promesse.

import client from "./client";

// --- Petit cache de session --------------------------------------------------
// Le catalogue ne change pas pendant qu'on l'utilise, et le plus gros jeu de
// données fait presque un mégaoctet. Le recharger à chaque clic d'onglet serait
// du gaspillage pur.
//
// Deux détails qui comptent :
//   - on stocke la PROMESSE, pas le résultat. Si l'utilisateur clique deux fois
//     rapidement, le second appel réutilise la requête en cours au lieu d'en
//     lancer une seconde.
//   - en cas d'échec on retire l'entrée, sinon une erreur réseau passagère
//     resterait mémorisée pour toute la session.
const cache = new Map();

function enCache(cle, chercher) {
  if (!cache.has(cle)) {
    cache.set(cle, chercher().catch((err) => { cache.delete(cle); throw err; }));
  }
  return cache.get(cle);
}

/** Les thèmes explorables — ceux dont les angles sont déclarés côté backend. */
export function getThemes() {
  return enCache("themes", async () => {
    const { data } = await client.get("/explorer/themes");
    return data;
  });
}

/** Les angles d'un thème et leurs variantes, tels que le catalogue les décrit. */
export function getCatalogue(theme) {
  return enCache(`cat:${theme}`, async () => {
    const { data } = await client.get(`/explorer/${theme}/catalogue`);
    return data;
  });
}

/**
 * Une valeur par territoire, pour un indicateur d'une table « longue ».
 *
 * ventilation : { sexe: "Ensemble", milieu: "Rural" } — vide quand l'indicateur
 * n'est pas détaillé, ce qui est le cas de toute la santé.
 */
export function getIndicateur(theme, cle, ventilation = {}) {
  return enCache(`ind:${theme}:${cle}:${JSON.stringify(ventilation)}`, async () => {
    // encodeURIComponent : une clé contenant « / » ou un accent casserait l'URL
    // et FastAPI chercherait une route qui n'existe pas.
    const { data } = await client.get(
      `/explorer/${theme}/indicateur/${encodeURIComponent(cle)}`,
      { params: ventilation }
    );
    return data;
  });
}

/** Les lignes brutes d'une table, avec ses colonnes filtrables. */
export function getJeu(theme, table) {
  return enCache(`jeu:${theme}:${table}`, async () => {
    const { data } = await client.get(`/explorer/${theme}/jeu/${encodeURIComponent(table)}`);
    return data;
  });
}
