import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  DEFAULT_FARM_CONTEXT,
  FARM_STORAGE_KEY,
  NAMIBIA_LOCATIONS,
} from "../utils/constants";
import { enqueueSync, saveFarmProfile } from "../db/offlineDb";
import { pushOfflineQueue } from "../services/syncService";

const FarmContext = createContext(null);

function loadStoredProfile() {
  try {
    const raw = localStorage.getItem(FARM_STORAGE_KEY);
    if (!raw) return DEFAULT_FARM_CONTEXT;
    const parsed = { ...DEFAULT_FARM_CONTEXT, ...JSON.parse(raw) };
    const known = NAMIBIA_LOCATIONS.some((loc) => loc.name === parsed.location);
    if (!known) {
      return { ...DEFAULT_FARM_CONTEXT };
    }
    return parsed;
  } catch {
    return DEFAULT_FARM_CONTEXT;
  }
}

export function FarmProvider({ children }) {
  const [context, setContext] = useState(loadStoredProfile);

  useEffect(() => {
    localStorage.setItem(FARM_STORAGE_KEY, JSON.stringify(context));
    const timer = setTimeout(() => {
      saveFarmProfile(context).catch(() => {});
      enqueueSync("farm_profile", context)
        .then(() => pushOfflineQueue())
        .catch(() => {});
    }, 400);
    return () => clearTimeout(timer);
  }, [context]);

  const update = useCallback((patch) => {
    setContext((prev) => ({ ...prev, ...patch }));
  }, []);

  const setLocationByName = useCallback((name) => {
    const match = NAMIBIA_LOCATIONS.find((loc) => loc.name === name);
    if (!match) {
      setContext((prev) => ({ ...prev, location: name }));
      return;
    }
    setContext((prev) => ({
      ...prev,
      location: match.name,
      region: match.region,
      lat: match.lat,
      lon: match.lon,
    }));
  }, []);

  const reset = useCallback(() => {
    setContext(DEFAULT_FARM_CONTEXT);
  }, []);

  const value = useMemo(
    () => ({
      ...context,
      update,
      setLocationByName,
      reset,
    }),
    [context, update, setLocationByName, reset]
  );

  return <FarmContext.Provider value={value}>{children}</FarmContext.Provider>;
}

export function useFarmContext() {
  const value = useContext(FarmContext);
  if (!value) {
    throw new Error("useFarmContext must be used within FarmProvider");
  }
  return value;
}
