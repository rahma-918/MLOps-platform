// frontend/src/components/MessageBubble.jsx
import SourcesList from "./SourcesList";
import { Sparkles, User, FileText } from "lucide-react";

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  // Gère à la fois le message frais (camelCase) et l'historique rechargé (snake_case)
  const docId = message.documentId || message.document_id_filter;
  const docName = message.documentName || message.document_name || "Document";

  return (
    <div className={`message-row ${isUser ? "from-user" : "from-assistant"}`}>
      <div className="message-avatar">
        {isUser ? <User size={14} /> : <Sparkles size={14} />}
      </div>

      <div className="message-content">
        {/* Bandeau document au-dessus de la bulle utilisateur */}
        {isUser && docId && (
          <div className="attached-document">
            <div className="attached-doc-inner">
              <FileText size={14} className="attached-doc-icon" />
              <span className="attached-doc-name">{docName}</span>
            </div>
          </div>
        )}

        <div className={`message-bubble ${isUser ? "bubble-user" : "bubble-assistant"}`}>
          {message.content}
        </div>

        {!isUser && <SourcesList sources={message.sources} />}
      </div>
    </div>
  );
}