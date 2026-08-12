// Signalement des actions au journal d'usage du serveur.
//
// Un export ou une impression se déroulent entièrement dans le navigateur :
// le fichier est fabriqué en mémoire puis remis à l'utilisateur, sans que le
// serveur en voie jamais passer la trace. C'est donc au client de le dire,
// sans quoi le compteur « rapports exportés » de l'espace d'administration
// resterait à zéro alors que la fonction est utilisée.
//
// Deux règles :
//   - on signale APRÈS le succès, jamais avant : un export qui échoue ne doit
//     pas gonfler le compteur ;
//   - on avale l'erreur. Si le serveur ne répond pas, le fichier a quand même
//     été produit ; tracer l'usage ne vaut pas d'interrompre l'usage.

import client from "./client";

export async function signaler(action, cible = null) {
  try {
    await client.post("/journal", { action, cible });
  } catch {
    // silencieux, volontairement (voir en-tête)
  }
}
