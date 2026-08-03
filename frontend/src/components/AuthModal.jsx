// frontend/src/components/AuthModal.jsx
import { useState } from "react";
import { LogIn, UserPlus, X, CheckCircle } from "lucide-react";
import { login, register } from "../api/client";
import { useAuth } from "../hooks/useAuth";

export default function AuthModal({ onClose, canClose = true }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const { setUser, checkAuth } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setIsLoading(true);

    try {
      if (mode === "login") {
        await login(email, password);
        await checkAuth();
        onClose();
      } else {
        // Inscription
        await register(email, password, fullName || undefined);
        // Bascule automatique vers le formulaire de connexion
        setMode("login");
        setSuccessMsg("Compte créé avec succès ! Veuillez vous connecter.");
        setPassword(""); // vide le mot de passe pour la connexion
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleMode = (newMode) => {
    setMode(newMode);
    setError(null);
    setSuccessMsg(null);
  };

  return (
    <div className="auth-modal-overlay" onClick={canClose ? onClose : undefined}>
      <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
        {canClose && (
          <button className="auth-modal-close" onClick={onClose}>
            <X size={18} />
          </button>
        )}

        <h2>{mode === "login" ? "Connexion" : "Créer un compte"}</h2>

        <form onSubmit={handleSubmit} className="auth-form">
          {mode === "register" && (
            <input
              type="text"
              placeholder="Nom complet (optionnel)"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          )}

          <input
            type="email"
            placeholder="Email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <input
            type="password"
            placeholder="Mot de passe"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {successMsg && (
            <span className="auth-success">
              <CheckCircle size={14} /> {successMsg}
            </span>
          )}

          {error && <span className="auth-error">{error}</span>}

          <button type="submit" disabled={isLoading} className="auth-submit">
            {isLoading
              ? "..."
              : mode === "login"
              ? "Se connecter"
              : "S'inscrire"}
          </button>
        </form>

        <p className="auth-toggle">
          {mode === "login" ? (
            <>
              Pas de compte ?{" "}
              <button type="button" onClick={() => toggleMode("register")}>
                S'inscrire
              </button>
            </>
          ) : (
            <>
              Déjà un compte ?{" "}
              <button type="button" onClick={() => toggleMode("login")}>
                Se connecter
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
}