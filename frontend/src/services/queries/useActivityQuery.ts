import { useQuery } from '@tanstack/react-query';
import { fetchHotspotActivity, type ActivityResponse } from '../hotspotService';

export function useActivityQuery(
  endDate: string,
  minConfidence?: number,
  state?: string,
) {
  return useQuery<ActivityResponse>({
    queryKey: ['hotspots-activity', { endDate, minConfidence, state }],
    queryFn: () => fetchHotspotActivity(endDate, minConfidence, state),
  });
}
