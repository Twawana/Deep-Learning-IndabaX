import { useQuery } from "@tanstack/react-query";
import { getDashboard } from "../services/api";
import { datasetLocation } from "../utils/constants";
import { getErrorMessage } from "../utils/format";
import { useFarmContext } from "../context/FarmContext";

function toOptionalInt(value) {
  if (value === "" || value === null || value === undefined) return undefined;
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

export function useDashboard() {
  const farm = useFarmContext();
  const location = datasetLocation(farm);
  const herdSize = toOptionalInt(farm.herdSize);

  const query = useQuery({
    queryKey: [
      "dashboard",
      location,
      farm.region,
      farm.lat,
      farm.lon,
      herdSize,
      farm.livestockType,
      farm.landTenure,
    ],
    enabled: Boolean(location),
    queryFn: () =>
      getDashboard({
        location,
        nearest_town: location,
        region: farm.region,
        lat: farm.lat,
        lon: farm.lon,
        herd_size: herdSize,
        livestock_type: farm.livestockType || "cattle",
        land_tenure: farm.landTenure,
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
