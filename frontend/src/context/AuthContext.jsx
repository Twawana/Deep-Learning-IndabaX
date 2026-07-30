import { createContext, useContext, useEffect, useMemo, useState } from "react";
import {
  createUser,
  deleteUser,
  getAdminState,
  loginAccount,
  logoutAccount,
  patchAdminSettings,
  patchUser,
  recordAiUsage,
  registerAccount,
  setSessionToken,
  upgradeSubscription,
} from "../services/api";

const AUTH_STORAGE_KEY = "farmar-auth-v2-cache";
const GUEST_ASK_KEY = "farmar-guest-asks-v1";
export const GUEST_ASK_LIMIT = 5;

const GUEST_USER = {
  id: "guest",
  name: "Guest",
  username: "guest",
  email: "",
  role: "guest",
  status: "active",
  tier: "free",
  aiUsage: 0,
  lastLogin: null,
};

const DEFAULT_STATE = {
  currentUser: GUEST_USER,
  isLoggedIn: false,
  users: [],
  appSettings: {
    maintenanceMode: false,
    allowDataSync: true,
  },
  source: "local-cache",
};

const AuthContext = createContext(null);

function mapUser(user) {
  if (!user) return GUEST_USER;
  return {
    id: user.id || "guest",
    name: user.name || "Guest",
    username: user.username || "",
    email: user.email || "",
    role: user.role || "guest",
    status: user.status || "active",
    tier: user.tier === "premium" ? "premium" : "free",
    aiUsage: Number(user.ai_usage ?? user.aiUsage ?? 0),
    lastLogin: user.last_login ?? user.lastLogin ?? null,
  };
}

function loadAuthState() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return DEFAULT_STATE;
    const parsed = JSON.parse(raw);
    return {
      ...DEFAULT_STATE,
      ...parsed,
      users: (parsed.users || []).map(mapUser),
      currentUser: mapUser(parsed.currentUser || GUEST_USER),
      isLoggedIn: Boolean(parsed.isLoggedIn),
    };
  } catch {
    return DEFAULT_STATE;
  }
}

function saveAuthState(state) {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(state));
}

export function AuthProvider({ children }) {
  const [state, setState] = useState(loadAuthState);
  const [loading, setLoading] = useState(true);
  const [guestAskCount, setGuestAskCount] = useState(() => {
    try {
      return Number(localStorage.getItem(GUEST_ASK_KEY) || 0);
    } catch {
      return 0;
    }
  });

  const updateState = (updater) => {
    setState((prev) => {
      const next = typeof updater === "function" ? updater(prev) : updater;
      saveAuthState(next);
      return next;
    });
  };

  const applyRemoteState = (data) => {
    if (data?.session_token) {
      setSessionToken(data.session_token);
    }
    const users = (data?.users || []).map(mapUser);
    const remoteCurrent = mapUser(data?.current_user || GUEST_USER);
    const loggedIn = Boolean(data?.is_logged_in) && remoteCurrent.id !== "guest";
    updateState((prev) => ({
      ...prev,
      currentUser: remoteCurrent,
      isLoggedIn: loggedIn,
      users: remoteCurrent.role === "admin" ? users : [],
      appSettings: {
        maintenanceMode: Boolean(data?.app_settings?.maintenance_mode),
        allowDataSync:
          data?.app_settings?.allow_data_sync === undefined
            ? true
            : Boolean(data.app_settings.allow_data_sync),
      },
      source: "backend",
    }));
  };

  useEffect(() => {
    let mounted = true;
    const hydrate = async () => {
      try {
        const data = await getAdminState();
        if (mounted) applyRemoteState(data);
      } catch {
        updateState((prev) => ({ ...prev, source: "local-cache" }));
      } finally {
        if (mounted) setLoading(false);
      }
    };
    hydrate();
    return () => {
      mounted = false;
    };
  }, []);

  const withBackendState = async (request) => {
    try {
      const data = await request();
      applyRemoteState(data);
      return { ok: true, message: data?.message || "Updated." };
    } catch (error) {
      const message =
        error?.response?.data?.detail || error?.message || "Request failed.";
      return { ok: false, message };
    }
  };

  const login = async (identifier, password) => {
    return withBackendState(() => loginAccount(identifier, password));
  };

  const register = async ({ name, email, username, password }) => {
    return withBackendState(() =>
      registerAccount({ name, email, username, password })
    );
  };

  const logout = async () => {
    const result = await withBackendState(() => logoutAccount());
    setSessionToken("");
    updateState((prev) => ({
      ...prev,
      currentUser: GUEST_USER,
      isLoggedIn: false,
      source: result.ok ? "backend" : prev.source,
    }));
    return result.ok
      ? result
      : { ok: true, message: "Logged out on this device." };
  };

  const upgradePlan = async (tier = "premium") => {
    return withBackendState(() => upgradeSubscription(tier));
  };

  const currentUser = state.currentUser || GUEST_USER;
  const userTier = currentUser?.tier === "premium" ? "premium" : "free";
  const isLoggedIn = Boolean(state.isLoggedIn) && currentUser.id !== "guest";
  const guestAsksRemaining = Math.max(0, GUEST_ASK_LIMIT - guestAskCount);
  const canAskAsGuest = guestAsksRemaining > 0;

  const trackAiUsage = async () => {
    if (!isLoggedIn) {
      setGuestAskCount((prev) => {
        const next = prev + 1;
        try {
          localStorage.setItem(GUEST_ASK_KEY, String(next));
        } catch {
          // ignore storage failures
        }
        return next;
      });
      return { ok: true, message: "Guest ask recorded." };
    }
    return withBackendState(() => recordAiUsage());
  };

  const addUser = async ({
    name,
    email,
    username,
    password = "changeme",
    role = "user",
    tier = "free",
  }) => {
    const cleanName = String(name || "").trim();
    if (!cleanName) return { ok: false, message: "User name is required." };
    return withBackendState(() =>
      createUser({
        name: cleanName,
        email: String(email || "").trim() || undefined,
        username: String(username || "").trim() || undefined,
        password,
        role: role === "admin" ? "admin" : "user",
        tier: tier === "premium" ? "premium" : "free",
      })
    );
  };

  const updateUser = async (userId, patch) => {
    return withBackendState(() =>
      patchUser(userId, {
        role: patch.role,
        status: patch.status,
        tier: patch.tier,
      })
    );
  };

  const removeUser = async (userId) => {
    return withBackendState(() => deleteUser(userId));
  };

  const updateSettings = async (patch) => {
    return withBackendState(() =>
      patchAdminSettings({
        maintenance_mode: patch.maintenanceMode,
        allow_data_sync: patch.allowDataSync,
      })
    );
  };

  const value = useMemo(
    () => ({
      users: state.users,
      currentUser,
      isLoggedIn,
      isAdmin: isLoggedIn && currentUser?.role === "admin",
      userTier,
      isPremium: isLoggedIn && userTier === "premium",
      guestAskCount,
      guestAskLimit: GUEST_ASK_LIMIT,
      guestAsksRemaining,
      canAskAsGuest,
      appSettings: state.appSettings,
      source: state.source,
      loading,
      login,
      register,
      logout,
      upgradePlan,
      trackAiUsage,
      addUser,
      updateUser,
      removeUser,
      updateSettings,
    }),
    [
      state,
      currentUser,
      userTier,
      isLoggedIn,
      loading,
      guestAskCount,
      guestAsksRemaining,
      canAskAsGuest,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return value;
}
