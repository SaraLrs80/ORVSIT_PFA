// Appels de la fiche territoriale pilotée par le catalogue.
//
// Deux routes seulement, et cette économie est voulue :
//   /familles  décrit la STRUCTURE (quelles familles, quelle forme, quelle
//              source). Elle ne dépend d'aucun territoire, donc le navigateur
//              la demande une fois par niveau et la garde.
//   /valeurs   apporte les CHIFFRES de tous les pairs d'un coup. Charger les
//              pairs en même temps que le territoire ouvert est ce qui permet
//              d'afficher un rang et un classement sans nouvel aller-retour
//              chaque fois qu'on change de territoire.
import client from "./client";

export async function getFamilles(niveau = "prefecture_province") {
  const reponse = await client.get("/fiche-nouvelle/familles", { params: { niveau } });
  return reponse.data;
}

// Au niveau communal, province_id est obligatoire : les pairs d'une commune
// sont les communes de SA province, jamais les 146 communes de la région.
export async function getValeurs(niveau = "prefecture_province", provinceId = null) {
  const params = { niveau };
  if (provinceId != null) params.province_id = provinceId;
  const reponse = await client.get("/fiche-nouvelle/valeurs", { params });
  return reponse.data;
}
