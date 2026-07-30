import { useMemo, useState } from "react";
import { Navigate } from "react-router-dom";
import Card from "../components/Card";
import { useAuth } from "../context/AuthContext";
import { FARM_STORAGE_KEY } from "../utils/constants";

export default function AdminPanel() {
  const {
    isAdmin,
    users,
    currentUser,
    appSettings,
    source,
    loading,
    addUser,
    updateUser,
    removeUser,
    updateSettings,
  } = useAuth();
  const [newUserName, setNewUserName] = useState("");
  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserRole, setNewUserRole] = useState("user");
  const [newUserTier, setNewUserTier] = useState("free");
  const [flash, setFlash] = useState("");

  const stats = useMemo(() => {
    const admins = users.filter((user) => user.role === "admin").length;
    const active = users.filter((user) => user.status === "active").length;
    const premium = users.filter((user) => user.tier === "premium").length;
    return {
      totalUsers: users.length,
      admins,
      active,
      premium,
    };
  }, [users]);

  if (!isAdmin) {
    return <Navigate to="/profile" replace />;
  }

  const handleAddUser = async (event) => {
    event.preventDefault();
    const result = await addUser({
      name: newUserName,
      email: newUserEmail,
      role: newUserRole,
      tier: newUserTier,
    });
    setFlash(result.message);
    if (result.ok) {
      setNewUserName("");
      setNewUserEmail("");
      setNewUserRole("user");
      setNewUserTier("free");
    }
  };

  const handleRoleChange = async (userId, role) => {
    const result = await updateUser(userId, { role });
    setFlash(result.message);
  };

  const handleStatusChange = async (userId, status) => {
    const result = await updateUser(userId, { status });
    setFlash(result.message);
  };

  const handleTierChange = async (userId, tier) => {
    const result = await updateUser(userId, { tier });
    setFlash(result.message);
  };

  const handleSettingsToggle = async (patch) => {
    const result = await updateSettings(patch);
    setFlash(result.message);
  };

  const handleRemoveUser = async (userId) => {
    const result = await removeUser(userId);
    setFlash(result.message);
  };

  const clearFarmData = () => {
    localStorage.removeItem(FARM_STORAGE_KEY);
    setFlash("Farm profile cache cleared. Reload to start from defaults.");
  };

  return (
    <div className="mx-auto w-full max-w-5xl space-y-4 pb-2">
      <Card title="Admin panel">
        <p className="text-sm text-ink-muted">
          Signed in as {currentUser.name}. Manage users, app settings, and local
          data.
        </p>
        <p className="mt-1 text-[11px] text-ink-muted">
          Auth source: {source === "backend" ? "Backend API" : "Local cache"}
          {loading ? " (syncing...)" : ""}
        </p>
        {flash ? <p className="mt-2 text-xs font-medium text-veld-700">{flash}</p> : null}
      </Card>

      <Card title="Platform status">
        <div className="grid grid-cols-2 gap-3 text-center sm:grid-cols-4">
          <StatTile label="Users" value={stats.totalUsers} />
          <StatTile label="Admins" value={stats.admins} />
          <StatTile label="Active" value={stats.active} />
          <StatTile label="Premium" value={stats.premium} />
        </div>
      </Card>

      <Card title="App controls">
        <div className="space-y-3">
          <ToggleRow
            label="Maintenance mode"
            hint="Blocks Ask for non-admins. Shows a banner across the app."
            value={appSettings.maintenanceMode}
            onChange={(next) => handleSettingsToggle({ maintenanceMode: next })}
          />
          <ToggleRow
            label="Allow data sync"
            hint="When off, farm profile still saves locally; remote admin sync stays available."
            value={appSettings.allowDataSync}
            onChange={(next) => handleSettingsToggle({ allowDataSync: next })}
          />
          <button
            type="button"
            onClick={clearFarmData}
            className="w-full rounded-xl border border-danger/20 bg-danger-bg px-3 py-2 text-sm font-semibold text-danger"
          >
            Clear cached farm data
          </button>
        </div>
      </Card>

      <Card title="Manage users">
        <div className="space-y-3">
          {users.map((user) => {
            const removable = user.id !== "admin-main";
            return (
              <div
                key={user.id}
                className="rounded-xl border border-veld-100 bg-mist p-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-ink">{user.name}</p>
                    <p className="text-xs text-ink-muted">
                      {user.email || user.username}
                      {user.aiUsage != null ? ` · AI asks: ${user.aiUsage}` : ""}
                    </p>
                  </div>
                  <span className="rounded-full bg-white px-2 py-1 text-[11px] font-semibold text-ink-muted ring-1 ring-veld-100">
                    {user.id === currentUser.id ? "Current" : "User"}
                  </span>
                </div>

                <div className="mt-3 grid grid-cols-3 gap-2">
                  <select
                    value={user.role}
                    onChange={(e) => handleRoleChange(user.id, e.target.value)}
                    className="field-input py-2"
                  >
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                  </select>
                  <select
                    value={user.status}
                    onChange={(e) => handleStatusChange(user.id, e.target.value)}
                    className="field-input py-2"
                  >
                    <option value="active">Active</option>
                    <option value="disabled">Disabled</option>
                  </select>
                  <select
                    value={user.tier || "free"}
                    onChange={(e) => handleTierChange(user.id, e.target.value)}
                    className="field-input py-2"
                  >
                    <option value="free">Free</option>
                    <option value="premium">Premium</option>
                  </select>
                </div>

                {removable ? (
                  <button
                    type="button"
                    onClick={() => handleRemoveUser(user.id)}
                    className="mt-2 text-xs font-semibold text-danger"
                  >
                    Remove user
                  </button>
                ) : null}
              </div>
            );
          })}
        </div>

        <form onSubmit={handleAddUser} className="mt-4 space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
            Add user
          </p>
          <input
            type="text"
            value={newUserName}
            onChange={(e) => setNewUserName(e.target.value)}
            placeholder="User name"
            className="field-input py-2"
          />
          <input
            type="email"
            value={newUserEmail}
            onChange={(e) => setNewUserEmail(e.target.value)}
            placeholder="Email (optional)"
            className="field-input py-2"
          />
          <select
            value={newUserRole}
            onChange={(e) => setNewUserRole(e.target.value)}
            className="field-input py-2"
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
          <select
            value={newUserTier}
            onChange={(e) => setNewUserTier(e.target.value)}
            className="field-input py-2"
          >
            <option value="free">Free</option>
            <option value="premium">Premium</option>
          </select>
          <button
            type="submit"
            className="w-full rounded-xl bg-veld-800 py-2.5 text-sm font-semibold text-white"
          >
            Add user
          </button>
        </form>
      </Card>
    </div>
  );
}

function StatTile({ label, value }) {
  return (
    <div className="rounded-xl border border-veld-100 bg-mist px-2 py-3">
      <p className="text-xl font-bold text-veld-900">{value}</p>
      <p className="text-xs text-ink-muted">{label}</p>
    </div>
  );
}

function ToggleRow({ label, hint, value, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!value)}
      className="flex w-full items-center justify-between gap-3 rounded-xl border border-veld-100 bg-mist px-3 py-2.5 text-left"
    >
      <span className="min-w-0">
        <span className="block text-sm font-medium text-ink">{label}</span>
        {hint ? (
          <span className="mt-0.5 block text-[11px] leading-snug text-ink-muted">
            {hint}
          </span>
        ) : null}
      </span>
      <span
        className={`shrink-0 rounded-full px-2 py-1 text-xs font-semibold ${
          value ? "bg-veld-100 text-veld-800" : "bg-white text-ink-muted"
        }`}
      >
        {value ? "On" : "Off"}
      </span>
    </button>
  );
}
