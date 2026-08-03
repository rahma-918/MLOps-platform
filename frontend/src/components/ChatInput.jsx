import { useState } from "react";
import { SendHorizontal } from "lucide-react";
import CategoryFilter from "./CategoryFilter";
import AdvancedOptions from "./AdvancedOptions";
import DocumentUpload from "./DocumentUpload";
import DomainSelector from "./DomainSelector";

export default function ChatInput({
  onSend,
  isSending,
  uploadedDocs,
  onDocumentUploaded,
  onRemoveDocument,
  activeDocumentId,
}) {
  const [text, setText] = useState("");
  const [categoryFilter, setCategoryFilter] = useState(null);
  const [domainFilter, setDomainFilter] = useState(null);
  const [options, setOptions] = useState({ useReranking: true, useMultiQuery: false });

  // Quand le domaine change, on reset la catégorie (elle n'existe plus dans la nouvelle taxonomie)
  const handleDomainChange = (newDomain) => {
    setDomainFilter(newDomain);
    setCategoryFilter(null); // ← IMPORTANT : évite une catégorie invalide
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!text.trim() || isSending) return;
    onSend(text.trim(), { categoryFilter, domainFilter, ...options });
    setText("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-input-area">
      <div className="chat-input-toolbar">
        <DocumentUpload
          uploadedDocs={uploadedDocs}
          onDocumentUploaded={onDocumentUploaded}
          onRemoveDocument={onRemoveDocument}
          activeDocumentId={activeDocumentId}
        />
        <DomainSelector value={domainFilter} onChange={handleDomainChange} />
        <CategoryFilter
          value={categoryFilter}
          onChange={setCategoryFilter}
          domain={domainFilter}   // ← PROP AJOUTÉE
        />
        <AdvancedOptions options={options} onChange={setOptions} />
      </div>

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <textarea
          rows={1}
          placeholder="Posez une question sur le corpus scientifique… (Shift+Entrée pour un saut de ligne)"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isSending}
        />
        <button type="submit" disabled={!text.trim() || isSending} aria-label="Envoyer">
          <SendHorizontal size={17} />
        </button>
      </form>
    </div>
  );
}