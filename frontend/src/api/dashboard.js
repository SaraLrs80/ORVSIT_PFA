// Appels liés aux tableaux de bord (données analytiques).
import client from "./client";

// Vue d'ensemble régionale : KPIs + classement des territoires par IDT.
export async function getApercu() {
  const response = await client.get("/overview");
  return response.data;
}
