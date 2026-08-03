// frontend/src/hooks/useConversation.js
import { useState, useCallback } from "react";
import { askQuestion, getConversation, listConversations } from "../api/client";

export function useConversation() {
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);
  const [uploadedDocs, setUploadedDocs] = useState([]);
  const [activeDocumentId, setActiveDocumentId] = useState(null);

  const addUploadedDocument = useCallback((doc) => {
  setUploadedDocs((prev) => [...prev, doc]);
  setActiveDocumentId(doc.document_id); // sélectionne automatiquement le document qu'on vient d'ajouter
}, []);

const removeUploadedDocument = useCallback((documentId) => {
  setUploadedDocs((prev) => prev.filter((d) => d.document_id !== documentId));
  setActiveDocumentId((current) => (current === documentId ? null : current));
}, []);

  const refreshConversations = useCallback(async () => {
    try {
      const list = await listConversations();
      setConversations(list);
    } catch (err) {
      console.error("Impossible de charger l'historique :", err);
    }
  }, []);

  const loadConversation = useCallback(async (id) => {
    setError(null);
    try {
      const conversation = await getConversation(id);
      setConversationId(conversation.id);
      setMessages(conversation.messages);
    } catch (err) {
      setError("Impossible de charger cette conversation.");
    }
  }, []);

  const startNewConversation = useCallback(() => {
    setConversationId(null);
    setMessages([]);
    setError(null);
  }, []);

  const resetAll = useCallback(() => {
    setConversationId(null);
    setMessages([]);
    setConversations([]);
    setUploadedDocs([]);
    setActiveDocumentId(null);
    setError(null);
  }, []);

  const sendMessage = useCallback(
    async (question, { categoryFilter, domainFilter, useReranking, useMultiQuery } = {}) => {
      setError(null);
      setIsSending(true);
      
      const activeDoc = uploadedDocs.find(d => d.document_id === activeDocumentId);
      // Affiche immédiatement le message utilisateur (optimistic UI)
      const userMessage = { id: `temp-${Date.now()}`, role: "user", content: question, documentId: activeDocumentId, documentName: activeDoc?.filename || null, };
      setMessages((prev) => [...prev, userMessage]);

      try {
        const response = await askQuestion({
          question,
          conversationId,
          categoryFilter,
          documentIdFilter: activeDocumentId,
          domainFilter,
          useReranking,
          useMultiQuery,
        });

        const assistantMessage = {
          id: `resp-${Date.now()}`,
          role: "assistant",
          content: response.answer,
          sources: response.sources,
          language_detected: response.language_detected,
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setConversationId(response.conversation_id);
        refreshConversations();
      } catch (err) {
        setError(err.message || "Une erreur est survenue.");
      } finally {
        setIsSending(false);
      }
    },
    [conversationId, activeDocumentId, uploadedDocs, refreshConversations]

  );

  return {
    conversationId,
    messages,
    conversations,
    isSending,
    error,
    sendMessage,
    startNewConversation,
    loadConversation,
    refreshConversations,
    uploadedDocs,
    addUploadedDocument,
    removeUploadedDocument,
    activeDocumentId,
    setActiveDocumentId,
    resetAll,
  };
}