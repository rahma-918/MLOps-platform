// frontend/src/components/ChatWindow.jsx
import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";
import EmptyState from "./EmptyState";

export default function ChatWindow({
  messages,
  isSending,
  error,
  onSend,
  uploadedDocs,
  onDocumentUploaded,
  onRemoveDocument,
  activeDocumentId,
}) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  return (
    <main className="chat-window">
      <div className="chat-messages">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
        )}

        {isSending && (
          <div className="message-row from-assistant">
            <div className="message-avatar">⋯</div>
            <div className="message-bubble bubble-assistant typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        )}

        {error && <div className="error-banner">{error}</div>}
        <div ref={endRef} />
      </div>

      <ChatInput
        onSend={onSend}
        isSending={isSending}
        uploadedDocs={uploadedDocs}
        onDocumentUploaded={onDocumentUploaded}
        onRemoveDocument={onRemoveDocument}
        activeDocumentId={activeDocumentId}
      />
    </main>
  );
}