import { useQuery } from "@tanstack/react-query";
import { getDashboard } from "../services/api";
import { getErrorMessage } from "../utils/format";
import { useFarmContext } from "../context/FarmContext";

export function useDashboard() {
  const farm = useFarmContext();

  const query = useQuery({
    queryKey: ["dashboard", farm.location, farm.lat, farm.lon],
    queryFn: () =>
      getDashboard({
        location: farm.location,
        region: farm.region,
        lat: farm.lat,
        lon: farm.lon,
        herd_size: farm.herdSize,
      }),
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error) : null,
    refetch: query.refetch,
  };
}
