// Appels liés à la page d'accueil du tableau de bord.
import client from "./client";

// L'état du catalogue : nombre d'indicateurs publiés par secteur, échelles
// servies, millésimes, organismes sources, part portant une définition
// rédigée. Le nom « aperçu » est conservé pour ne pas casser les appels
// existants, mais la route ne renvoie plus l'indice composite abandonné.
export async function getApercu() {
  const response = await client.get("/overview");
  return response.data;
}
