import { useEffect, useState, useRef } from "react";
import { LogOut, User, Menu, X } from "lucide-react";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import AuthModal from "./components/AuthModal";
import { useConversation } from "./hooks/useConversation";
import { useAuth } from "./hooks/useAuth";
import { AuthProvider } from "./context/AuthContext";
import "./index.css";
import "./chat.css";
import "./auth.css";

function AppInner() {
  const { user, loading: authLoading, doLogout } = useAuth();
  const [showAuth, setShowAuth] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const prevUserIdRef = useRef(undefined);

  const {
    conversationId, messages, conversations, isSending, error,
    uploadedDocs, addUploadedDocument, removeUploadedDocument,
    activeDocumentId, setActiveDocumentId,
    sendMessage, startNewConversation, loadConversation, refreshConversations,
    resetAll,
  } = useConversation();

  // Ouvre la modale une fois l'authentification connue ET si non connecté
  useEffect(() => {
    if (!authLoading && !user) {
      setShowAuth(true);
    }
  }, [authLoading, user]);

  // Réinitialise TOUT l'état de conversation à chaque changement d'utilisateur
  // (connexion, déconnexion, ou changement de compte) -- évite qu'un historique
  // d'un utilisateur précédent reste affiché après un changement de session.
  useEffect(() => {
    const currentId = user?.id ?? null;
    if (currentId !== prevUserIdRef.current) {
      resetAll();
      if (currentId) {
        refreshConversations();
      }
      prevUserIdRef.current = currentId;
    }
  }, [user, resetAll, refreshConversations]);

  const handleCloseAuth = () => setShowAuth(false);

  return (
    <div className="app-shell">
      {sidebarOpen && (
        <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} />
      )}
      <Sidebar
        conversations={conversations}
        activeId={conversationId}
        onNewChat={() => {
          startNewConversation();
          setSidebarOpen(false);
        }}
        onSelectConversation={(id) => {
          loadConversation(id);
          setSidebarOpen(false);
        }}
        className={sidebarOpen ? "open" : ""}
      />

      <div className="main-area">
        <header className="app-header">
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen((o) => !o)}
            aria-label="Ouvrir le menu"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <div className="app-header-spacer" />
          {user ? (
            <div className="user-menu">
              <span className="user-name">
                <User size={14} /> {user.full_name || user.email}
              </span>
              <button onClick={doLogout} className="logout-btn" title="Déconnexion">
                <LogOut size={14} />
              </button>
            </div>
          ) : (
            <button onClick={() => setShowAuth(true)} className="login-trigger">
              Connexion
            </button>
          )}
        </header>

        <ChatWindow
          messages={messages}
          isSending={isSending}
          error={error}
          onSend={sendMessage}
          uploadedDocs={uploadedDocs}
          onDocumentUploaded={addUploadedDocument}
          onRemoveDocument={removeUploadedDocument}
          activeDocumentId={activeDocumentId}
        />
      </div>

      {showAuth && <AuthModal onClose={handleCloseAuth} canClose={!!user} />}
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  );
}