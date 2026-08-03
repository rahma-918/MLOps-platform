import { createContext, useState, useEffect, useCallback } from "react";
import { getMe, logout, getToken } from "../api/client";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    try {
      const me = await getMe();
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const doLogout = useCallback(async () => {
    await logout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, setUser, loading, doLogout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}