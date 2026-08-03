import { FileText } from "lucide-react";


const CHIP_COLORS = ["#2dd4a7", "#8b5cf6", "#f5a85c", "#5cc8f5", "#e5726b", "#c9d15c"];

function colorForSource(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return CHIP_COLORS[Math.abs(hash) % CHIP_COLORS.length];
}

export default function SourcesList({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="sources-strip">
      <span className="sources-label">Sources</span>
      <div className="sources-chips">
        {sources.map((src, idx) => (
          <span
            key={idx}
            className="source-chip"
            style={{ borderColor: colorForSource(src.source_file) }}
          >
            <FileText size={11} />
            {src.source_file}
            <span className="source-page">p.{src.page_or_section}</span>
          </span>
        ))}
      </div>
    </div>
  );
}