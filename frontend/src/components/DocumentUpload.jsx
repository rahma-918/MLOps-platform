// frontend/src/components/DocumentUpload.jsx
import { useState, useRef } from "react";
import { Paperclip, FileCheck, Loader2, X } from "lucide-react";
import { uploadDocument } from "../api/client";

export default function DocumentUpload({
  uploadedDocs,
  onDocumentUploaded,
  onRemoveDocument,
  activeDocumentId,
}) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsUploading(true);
    setError(null);

    try {
      const result = await uploadDocument(file);
      onDocumentUploaded(result);
    } catch (err) {
      setError(err.message || "Échec de l'upload");
    } finally {
      setIsUploading(false);
      e.target.value = "";
    }
  };

  const activeDoc = uploadedDocs.find((d) => d.document_id === activeDocumentId);

  return (
    <div className="document-upload">
      <input
        type="file"
        ref={inputRef}
        style={{ display: "none" }}
        accept=".pdf,.docx,.png,.jpg,.jpeg"
        onChange={handleFileSelect}
      />

      <button
        type="button"
        className="upload-trigger"
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
      >
        {isUploading ? <Loader2 size={14} className="spin" /> : <Paperclip size={14} />}
        {isUploading ? "Analyse en cours…" : "Ajouter un document"}
      </button>

      {error && <span className="upload-error">{error}</span>}

      {/* Affiche UNIQUEMENT le document actif (pas l'historique complet) */}
      {activeDoc && (
        <div className="uploaded-docs-list">
          <span className="uploaded-doc-chip active-doc-chip">
            <FileCheck size={12} />
            {activeDoc.filename}
            <button
              type="button"
              onClick={() => onRemoveDocument(activeDoc.document_id)}
              aria-label="Retirer"
            >
              <X size={12} />
            </button>
          </span>
        </div>
      )}
    </div>
  );
}