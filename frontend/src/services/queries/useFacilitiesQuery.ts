import { useQuery } from '@tanstack/react-query';
import { fetchFacilities } from '../facilityService';
import type { Facility } from '../../types/facility';

export function useFacilitiesQuery() {
  return useQuery<Facility[]>({
    queryKey: ['facilities'],
    queryFn: fetchFacilities,
  });
}
