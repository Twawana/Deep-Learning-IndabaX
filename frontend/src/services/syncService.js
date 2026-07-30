/**
 * Sync device offline store → Supabase PostgreSQL (via FastAPI /sync).
 * Runs when the browser/device is online.
 */

import api from "./api";
import {
  clearSyncQueue,
  getDeviceId,
  listSyncQueue,
  setMeta,
} from "../db/offlineDb";

let syncing = false;

export async function pushOfflineQueue(userId = null) {
  if (typeof navigator !== "undefined" && !navigator.onLine) {
    return { ok: false, message: "Offline — queue kept on device.", applied: 0 };
  }
  if (syncing) {
    return { ok: false, message: "Sync already in progress.", applied: 0 };
  }

  syncing = true;
  try {
    const items = await listSyncQueue();
    if (!items.length) {
      return { ok: true, message: "Nothing to sync.", applied: 0 };
    }

    const deviceId = await getDeviceId();
    const { data } = await api.post("/sync/push", {
      device_id: deviceId,
      user_id: userId || undefined,
      items: items.map((item) => ({
        type: item.type,
        payload: item.payload,
        client_id: item.client_id,
        created_at: item.created_at,
      })),
    });

    // Clear successfully applied items (best-effort: clear all if applied > 0)
    if ((data?.applied || 0) > 0) {
      await clearSyncQueue(items.map((i) => i.id));
      await setMeta("last_sync_at", new Date().toISOString());
    }
    return {
      ok: Boolean(data?.ok ?? true),
      message: data?.message || "Sync finished.",
      applied: data?.applied || 0,
      errors: data?.errors || [],
      supabase: true,
    };
  } catch (error) {
    const message =
      error?.response?.data?.detail ||
      error?.message ||
      "Sync failed — will retry when online.";
    return { ok: false, message, applied: 0 };
  } finally {
    syncing = false;
  }
}

export async function fetchSyncStatus() {
  try {
    const { data } = await api.get("/sync/status");
    return data;
  } catch {
    return {
      supabase_configured: false,
      offline_store: "device SQLite / IndexedDB",
      cloud_store: "unreachable",
    };
  }
}

export function startAutoSync(getUserId) {
  const run = () => {
    const userId = typeof getUserId === "function" ? getUserId() : null;
    pushOfflineQueue(userId).catch(() => {});
  };
  if (typeof window === "undefined") return () => {};
  window.addEventListener("online", run);
  // Initial attempt shortly after boot
  const t = setTimeout(run, 2500);
  return () => {
    window.removeEventListener("online", run);
    clearTimeout(t);
  };
}
