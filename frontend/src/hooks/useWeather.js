import { useCallback, useEffect, useState } from "react";
import { getWeather } from "../services/api";
import { datasetLocation } from "../utils/constants";
import { getErrorMessage } from "../utils/format";
import { useFarmContext } from "../context/FarmContext";

export function useWeather() {
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

  const fetchWeather = useCallback(async (lat, lon, extra = {}) => {
    const location = (extra.location || extra.nearest_town || "").trim();
    if (!location) {
      setError("Please select a supported town or research site.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await getWeather(lat, lon, {
        ...extra,
        location,
      });
      setData(result);
    } catch (err) {
      setData(null);
      setError(getErrorMessage(err, "Failed to load weather data."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { data, isLoading, error, fetchWeather, setError };
}
