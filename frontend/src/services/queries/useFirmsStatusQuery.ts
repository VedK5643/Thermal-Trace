import { useQuery } from '@tanstack/react-query';
import api from '../api';

export interface FirmsStatus {
  status: 'live' | 'delayed' | 'stale' | 'degraded';
  lastSyncSuccessAt: string | null;
  latestObservationAt: string | null;
  nextScheduledSyncAt: string;
  satellites: string[];
  observationsIngested: number;
}

export function useFirmsStatusQuery() {
  return useQuery<FirmsStatus>({
    queryKey: ['firms-status'],
    queryFn: async () => {
      const res = await api.get('/api/v1/firms/status');
      return res.data;
    },
    refetchInterval: 120000, // Poll lightweight status metadata every 2 minutes
    staleTime: 60000,
  });
}
