import { Plus, Search, MessageSquare } from "lucide-react";
import { useState, useMemo } from "react";

export default function Sidebar({ conversations, activeId, onNewChat, onSelectConversation, className = "" }) {
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim()) return conversations;
    return conversations.filter((c) =>
      (c.title || "Sans titre").toLowerCase().includes(search.toLowerCase())
    );
  }, [conversations, search]);

  return (
    <aside className={`sidebar ${className}`}>
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <span className="sidebar-brand-mark">◆</span>
          <span>Évidence</span>
        </div>
        <button className="new-chat-btn" onClick={onNewChat}>
          <Plus size={16} /> Nouvelle conversation
        </button>
      </div>

      <div className="sidebar-search">
        <Search size={15} />
        <input
          type="text"
          placeholder="Rechercher une conversation…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="sidebar-list">
        <p className="sidebar-list-label">Conversations récentes</p>
        {filtered.length === 0 && (
          <p className="sidebar-empty">Aucune conversation pour l'instant.</p>
        )}
        {filtered.map((conv) => (
          <button
            key={conv.id}
            className={`conversation-item ${conv.id === activeId ? "active" : ""}`}
            onClick={() => onSelectConversation(conv.id)}
          >
            <MessageSquare size={15} />
            <span className="conversation-title">{conv.title || "Sans titre"}</span>
          </button>
        ))}
      </div>
    </aside>
  );
}