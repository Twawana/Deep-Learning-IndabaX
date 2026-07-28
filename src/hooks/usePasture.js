import { useCallback, useState } from "react";
import { getPasture } from "../services/api";
import { getErrorMessage } from "../utils/format";

export function usePasture() {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchPasture = useCallback(async (location) => {
    const trimmed = location?.trim();
    if (!trimmed) {
      setError("Please select or enter a location.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await getPasture(trimmed);
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
