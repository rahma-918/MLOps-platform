import { useState } from "react";
import { SlidersHorizontal, ChevronDown } from "lucide-react";

export default function AdvancedOptions({ options, onChange }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="advanced-options">
      <button className="advanced-toggle" onClick={() => setOpen((o) => !o)}>
        <SlidersHorizontal size={14} />
        Options avancées
        <ChevronDown size={14} className={open ? "rotated" : ""} />
      </button>

      {open && (
        <div className="advanced-panel">
          <label className="advanced-row">
            <input
              type="checkbox"
              checked={options.useReranking}
              onChange={(e) => onChange({ ...options, useReranking: e.target.checked })}
            />
            Reranking (affine la pertinence des sources)
          </label>
          <label className="advanced-row">
            <input
              type="checkbox"
              checked={options.useMultiQuery}
              onChange={(e) => onChange({ ...options, useMultiQuery: e.target.checked })}
            />
            Reformulation multiple de la question
          </label>
        </div>
      )}
    </div>
  );
}