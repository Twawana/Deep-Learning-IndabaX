import { createContext, useContext, useEffect, useMemo, useState } from "react";
import {
  createUser,
  deleteUser,
  getAdminState,
  loginAdmin,
  logoutAccount,
  patchAdminSettings,
  patchUser,
  switchAccount,
} from "../services/api";

const AUTH_STORAGE_KEY = "farmar-auth-v1-cache";

const DEFAULT_USERS = [
  {
    id: "user-main",
    name: "Farm User",
    email: "farmer@farmar.local",
    role: "user",
    status: "active",
    lastLogin: null,
  },
  {
    id: "admin-main",
    name: "Admin",
    email: "admin@farmar.local",
    role: "admin",
    status: "active",
    lastLogin: null,
  },
];

const DEFAULT_STATE = {
  currentUser: DEFAULT_USERS[0],
  users: DEFAULT_USERS,
  appSettings: {
    maintenanceMode: false,
    allowDataSync: true,
  },
  source: "local-cache",
};

const AuthContext = createContext(null);

function loadAuthState() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return DEFAULT_STATE;
    const parsed = JSON.parse(raw);
    return {
      ...DEFAULT_STATE,
      ...DEFAULT_STATE,
      ...parsed,
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

  const updateState = (updater) => {
    setState((prev) => {
      const next = typeof updater === "function" ? updater(prev) : updater;
      saveAuthState(next);
      return next;
    });
  };

  const applyRemoteState = (data) => {
    const users =
      data?.users?.map((user) => ({
        id: user.id,
        name: user.name,
        email: user.email,
        role: user.role,
        status: user.status,
        lastLogin: user.last_login ?? null,
      })) || DEFAULT_USERS;
    const remoteCurrent = data?.current_user || users[0];
    updateState((prev) => ({
      ...prev,
      currentUser: {
        id: remoteCurrent.id,
        name: remoteCurrent.name,
        email: remoteCurrent.email,
        role: remoteCurrent.role,
        status: remoteCurrent.status,
        lastLogin: remoteCurrent.last_login ?? null,
      },
      users,
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

  const loginAsUser = async (userId) => {
    return withBackendState(() => switchAccount(userId));
  };

  const loginAsAdmin = async (passcode) => {
    return withBackendState(() => loginAdmin(passcode));
  };

  const logout = async () => {
    return withBackendState(() => logoutAccount());
  };

  const addUser = async ({ name, email, role = "user" }) => {
    const cleanName = String(name || "").trim();
    if (!cleanName) return { ok: false, message: "User name is required." };
    return withBackendState(() =>
      createUser({
        name: cleanName,
        email: String(email || "").trim() || undefined,
        role: role === "admin" ? "admin" : "user",
      })
    );
  };

  const updateUser = async (userId, patch) => {
    return withBackendState(() =>
      patchUser(userId, {
        role: patch.role,
        status: patch.status,
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

  const currentUser = state.currentUser || state.users[0];

  const value = useMemo(
    () => ({
      users: state.users,
      currentUser,
      isAdmin: currentUser?.role === "admin",
      appSettings: state.appSettings,
      source: state.source,
      loading,
      loginAsUser,
      loginAsAdmin,
      logout,
      addUser,
      updateUser,
      removeUser,
      updateSettings,
    }),
    [state, currentUser, loading]
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
