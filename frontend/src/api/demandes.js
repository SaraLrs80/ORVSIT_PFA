// Appel(s) liés aux demandes d'accès (partie publique).
import client from "./client";

// Envoie le formulaire public au backend : POST /demandes/
// payload = { nom_complet, email, organisation, profil_souhaite, motif }
export async function creerDemande(payload) {
  const { data } = await client.post("/demandes/", payload);
  return data;
}
