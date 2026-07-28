import { useQuery } from "@tanstack/react-query";
import { getDashboard } from "../services/api";
import { getErrorMessage } from "../utils/format";

export function useDashboard() {
  const query = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error ? getErrorMessage(query.error) : null,
    refetch: query.refetch,
  };
}
