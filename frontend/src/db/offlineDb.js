/**
 * Device offline store — SQLite-shaped tables on the phone/browser.
 *
 * Web / Capacitor WebView: IndexedDB (same schema as planned native SQLite).
 * Native path later: swap openDb() to @capacitor-community/sqlite without
 * changing callers.
 *
 * Tables:
 *   rangeland_cache   — cached pasture/weather payloads by location
 *   chat_messages     — previous AI Q&A
 *   farm_profile      — user inputs (location, herd, …)
 *   sync_queue        — unsynced requests waiting for connectivity
 *   meta              — device_id, last_sync_at, …
 */

const DB_NAME = "farmar-oryx-offline";
const DB_VERSION = 1;

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("rangeland_cache")) {
        db.createObjectStore("rangeland_cache", { keyPath: "location_key" });
      }
      if (!db.objectStoreNames.contains("chat_messages")) {
        const chat = db.createObjectStore("chat_messages", { keyPath: "id" });
        chat.createIndex("by_created", "created_at");
      }
      if (!db.objectStoreNames.contains("farm_profile")) {
        db.createObjectStore("farm_profile", { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains("sync_queue")) {
        const q = db.createObjectStore("sync_queue", {
          keyPath: "id",
          autoIncrement: true,
        });
        q.createIndex("by_created", "created_at");
      }
      if (!db.objectStoreNames.contains("meta")) {
        db.createObjectStore("meta", { keyPath: "key" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function txDone(tx) {
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error || new Error("transaction aborted"));
  });
}

function reqToPromise(req) {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function uuid() {
  if (crypto?.randomUUID) return crypto.randomUUID();
  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export async function getDeviceId() {
  const db = await openDb();
  const tx = db.transaction("meta", "readwrite");
  const store = tx.objectStore("meta");
  let row = await reqToPromise(store.get("device_id"));
  if (!row?.value) {
    row = { key: "device_id", value: uuid() };
    store.put(row);
  }
  await txDone(tx);
  db.close();
  return row.value;
}

export async function cacheRangeland(locationKey, payload) {
  if (!locationKey) return;
  const db = await openDb();
  const tx = db.transaction("rangeland_cache", "readwrite");
  tx.objectStore("rangeland_cache").put({
    location_key: String(locationKey).toLowerCase(),
    payload,
    updated_at: new Date().toISOString(),
  });
  await txDone(tx);
  db.close();
}

export async function getCachedRangeland(locationKey) {
  if (!locationKey) return null;
  const db = await openDb();
  const tx = db.transaction("rangeland_cache", "readonly");
  const row = await reqToPromise(
    tx.objectStore("rangeland_cache").get(String(locationKey).toLowerCase())
  );
  await txDone(tx);
  db.close();
  return row?.payload || null;
}

export async function saveFarmProfile(farm) {
  const db = await openDb();
  const tx = db.transaction("farm_profile", "readwrite");
  tx.objectStore("farm_profile").put({
    id: "current",
    ...farm,
    updated_at: new Date().toISOString(),
  });
  await txDone(tx);
  db.close();
}

export async function loadFarmProfile() {
  const db = await openDb();
  const tx = db.transaction("farm_profile", "readonly");
  const row = await reqToPromise(tx.objectStore("farm_profile").get("current"));
  await txDone(tx);
  db.close();
  return row || null;
}

export async function saveChatMessage(message) {
  const db = await openDb();
  const tx = db.transaction("chat_messages", "readwrite");
  const row = {
    id: message.id || uuid(),
    role: message.role,
    content: message.content,
    location: message.location || null,
    agent: message.agent || null,
    mode: message.mode || null,
    tools_used: message.tools_used || null,
    decision: message.decision || null,
    created_at: message.timestamp || message.created_at || new Date().toISOString(),
    synced: Boolean(message.synced),
  };
  tx.objectStore("chat_messages").put(row);
  await txDone(tx);
  db.close();
  return row;
}

export async function listChatMessages(limit = 100) {
  const db = await openDb();
  const tx = db.transaction("chat_messages", "readonly");
  const all = await reqToPromise(tx.objectStore("chat_messages").getAll());
  await txDone(tx);
  db.close();
  return (all || [])
    .sort((a, b) => String(a.created_at).localeCompare(String(b.created_at)))
    .slice(-limit);
}

export async function enqueueSync(type, payload) {
  const db = await openDb();
  const tx = db.transaction("sync_queue", "readwrite");
  tx.objectStore("sync_queue").add({
    type,
    payload,
    created_at: new Date().toISOString(),
    client_id: uuid(),
  });
  await txDone(tx);
  db.close();
}

export async function listSyncQueue() {
  const db = await openDb();
  const tx = db.transaction("sync_queue", "readonly");
  const all = await reqToPromise(tx.objectStore("sync_queue").getAll());
  await txDone(tx);
  db.close();
  return all || [];
}

export async function clearSyncQueue(ids) {
  if (!ids?.length) return;
  const db = await openDb();
  const tx = db.transaction("sync_queue", "readwrite");
  const store = tx.objectStore("sync_queue");
  for (const id of ids) store.delete(id);
  await txDone(tx);
  db.close();
}

export async function setMeta(key, value) {
  const db = await openDb();
  const tx = db.transaction("meta", "readwrite");
  tx.objectStore("meta").put({ key, value });
  await txDone(tx);
  db.close();
}

export async function getMeta(key, fallback = null) {
  const db = await openDb();
  const tx = db.transaction("meta", "readonly");
  const row = await reqToPromise(tx.objectStore("meta").get(key));
  await txDone(tx);
  db.close();
  return row ? row.value : fallback;
}
