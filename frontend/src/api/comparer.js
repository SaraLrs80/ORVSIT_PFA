// Appels liés à la comparaison de territoires.
import client from "./client";

// Compare 2 à 3 territoires de même niveau.
// ids : tableau d'identifiants, ex. [2, 9, 8]
export async function getComparaison(ids) {
  const response = await client.get("/comparer", {
    params: { ids: ids.join(",") },
  });
  return response.data;
}
