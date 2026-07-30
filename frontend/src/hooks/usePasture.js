import { useCallback, useEffect, useState } from "react";
import { getPasture } from "../services/api";
import { datasetLocation } from "../utils/constants";
import { getErrorMessage } from "../utils/format";
import { useFarmContext } from "../context/FarmContext";

export function usePasture() {
  const farm = useFarmContext();
  const locationKey = datasetLocation(farm);
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Drop stale results when the farmer changes town/site
  useEffect(() => {
    setData(null);
    setError(null);
  }, [locationKey]);

  const fetchPasture = useCallback(async (location, extra = {}) => {
    const trimmed = location?.trim();
    if (!trimmed) {
      setError("Please select a supported town or research site.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await getPasture(trimmed, extra);
      setData(result);
    } catch (err) {
      setData(null);
      setError(getErrorMessage(err, "Failed to load pasture data."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { data, isLoading, error, fetchPasture, setError };
}
