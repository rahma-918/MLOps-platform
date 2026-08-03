import { useState } from "react";
import { Globe, Stethoscope, Cpu, Scale } from "lucide-react";

const DOMAINS = [
  { value: null, label: "Auto-détection", icon: Globe },
  { value: "medical", label: "Santé / Médical", icon: Stethoscope },
  { value: "technical", label: "Technique / IT", icon: Cpu },
  { value: "legal", label: "Juridique", icon: Scale },
];

export default function DomainSelector({ value, onChange }) {
  return (
    <div className="domain-selector">
      <select
        value={value || ""}
        onChange={(e) => onChange(e.target.value || null)}
        title="Domaine du document"
      >
        {DOMAINS.map((d) => (
          <option key={d.value || "auto"} value={d.value || ""}>
            {d.label}
          </option>
        ))}
      </select>
    </div>
  );
}