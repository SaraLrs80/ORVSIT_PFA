// Appels de l'assistant conversationnel.
//
// Quatre routes, et une seule subtilité : l'ÉTAT de la conversation ne
// voyage pas. Le navigateur n'envoie que la question et un identifiant ; le
// serveur retrouve lui-même le dernier territoire et le dernier indicateur en
// lisant les références du dernier message. C'est ce qui permet à « et pour
// Larache ? » de fonctionner après un rechargement de page.

import client from "./client";

export async function poserQuestion(question, conversationId = null) {
  const reponse = await client.post("/assistant/question", {
    question,
    conversation_id: conversationId,
  });
  return reponse.data;
}

export async function listerConversations() {
  const reponse = await client.get("/assistant/conversations");
  return reponse.data;
}

export async function lireFil(conversationId) {
  const reponse = await client.get(`/assistant/conversation/${conversationId}`);
  return reponse.data;
}

export async function renommerConversation(conversationId, titre) {
  const reponse = await client.patch(`/assistant/conversation/${conversationId}`,
                                     { titre });
  return reponse.data;
}

export async function supprimerConversation(conversationId) {
  await client.delete(`/assistant/conversation/${conversationId}`);
}

// L'avis ne doit jamais gêner : s'il échoue, la conversation continue.
export async function donnerUnAvis(messageId, utile, commentaire = null) {
  try {
    await client.post(`/assistant/message/${messageId}/avis`, {
      utile,
      commentaire,
    });
    return true;
  } catch {
    return false;
  }
}
