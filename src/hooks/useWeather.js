import { useCallback, useState } from "react";
import { getWeather } from "../services/api";
import { getErrorMessage } from "../utils/format";

export function useWeather() {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchWeather = useCallback(async (lat, lon) => {
    const latitude = Number(lat);
    const longitude = Number(lon);

    if (Number.isNaN(latitude) || Number.isNaN(longitude)) {
      setError("Please provide valid latitude and longitude values.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await getWeather(latitude, longitude);
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
