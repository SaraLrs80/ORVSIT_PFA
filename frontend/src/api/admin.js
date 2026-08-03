import client from "./client";

export async function listerDemandes(statut) {
  const params = statut ? { statut } : {};
  const response = await client.get("/admin/demandes", { params });
  return response.data;
}

export async function approuverDemande(demandeId) {
  const response = await client.post(`/admin/demandes/${demandeId}/approuver`);
  return response.data;
}   

export async function rejeterDemande(demandeId) {
  const response = await client.post(`/admin/demandes/${demandeId}/rejeter`);
  return response.data;
}

// --- Utilisateurs ---

export async function listerUtilisateurs() {
  const response = await client.get("/admin/utilisateurs");
  return response.data;
}

export async function supprimerUtilisateur(utilisateurId) {
  const response = await client.delete(`/admin/utilisateurs/${utilisateurId}`);
  return response.data;
}   


// changements = { role?, statut?, organisation? } — on n'envoie que ce qu'on modifie
export async function modifierUtilisateur(utilisateurId, changements) {
  const response = await client.patch(
    `/admin/utilisateurs/${utilisateurId}`,
    changements
  );
  return response.data;
}

// payload = { nom_complet, email, role, organisation }
export async function ajouterUtilisateur(payload) {
  const response = await client.post("/admin/utilisateurs/ajouter", payload);
  return response.data;
}

// --- Statistiques d'usage (supervision) ---
export async function getStatistiques() {
  const response = await client.get("/admin/statistiques");
  return response.data;
}