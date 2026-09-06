import { useQuery } from '@tanstack/react-query';
import { fetchHotspots } from '../hotspotService';
import type { Hotspot } from '../../types/hotspot';

export function useHotspotsQuery(
  date?: string,
  minConfidence?: number,
  state?: string,
) {
  return useQuery<Hotspot[]>({
    queryKey: ['hotspots', { date, minConfidence, state }],
    queryFn: () => fetchHotspots(date, minConfidence, state),
  });
}
