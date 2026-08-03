const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// --- Token management ---
export function getToken() {
  return localStorage.getItem("access_token");
}

export function setToken(token) {
  localStorage.setItem("access_token", token);
}

export function removeToken() {
  localStorage.removeItem("access_token");
}

// --- Intercepteur de fetch avec Bearer ---
async function authFetch(url, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
    credentials: "include",   // ← ENVOIE/REÇOIT les cookies (refresh_token)
  });

  if (response.status === 401) {
    // Tentative de refresh automatique
    const refreshed = await refreshToken();
    if (refreshed) {
      // Retry avec le nouveau token
      return authFetch(url, options);
    } else {
      removeToken();
      throw new Error("Session expirée. Veuillez vous reconnecter.");
    }
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Erreur ${response.status}`);
  }

  return response.json();
}

async function refreshToken() {
  try {
    const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) return false;
    const data = await res.json();
    setToken(data.access_token);
    return true;
  } catch {
    return false;
  }
}

// --- API endpoints ---
export async function login(email, password) {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Échec de la connexion");
  }
  const data = await res.json();
  setToken(data.access_token);
  return data;
}

export async function register(email, password, full_name) {
  const res = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Échec de l'inscription");
  }
  return res.json();
}

export async function logout() {
  await fetch(`${API_BASE_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
  removeToken();
}

export async function getMe() {
  return authFetch("/auth/me");
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const token = getToken();
  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    body: formData,
    credentials: "include",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Erreur ${response.status}`);
  }
  return response.json();
}

export function askQuestion({ question, conversationId, categoryFilter, documentIdFilter, domainFilter, useReranking = true, useMultiQuery = false }) {
  return authFetch("/ask", {
    method: "POST",
    body: JSON.stringify({
      question,
      conversation_id: conversationId || null,
      category_filter: categoryFilter || null,
      document_id_filter: documentIdFilter || null,
      domain_filter: domainFilter || null, 
      use_reranking: useReranking,
      use_multi_query: useMultiQuery,
    }),
  });
}

export function listConversations() {
  return authFetch("/conversations");
}

export function getConversation(conversationId) {
  return authFetch(`/conversations/${conversationId}`);
}

export function getCategories(domain = null) {
  const qs = domain ? `?domain=${encodeURIComponent(domain)}` : "";
  return authFetch(`/categories${qs}`);
}
export function checkHealth() {
  return fetch(`${API_BASE_URL}/health`).then(r => r.json());
}