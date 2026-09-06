import { useQuery } from '@tanstack/react-query';
import { fetchAlerts } from '../alertService';
import type { Alert } from '../../types/alert';
import { useMapStore } from '../../store/mapStore';

export function useAlertsQuery(date?: string) {
  const selectedDate = useMapStore((s) => s.selectedDate);
  const targetDate = date || selectedDate;

  return useQuery<Alert[]>({
    queryKey: ['alerts', targetDate],
    queryFn: () => fetchAlerts(targetDate),
    refetchInterval: 10000,
    staleTime: 5000,
  });
}
