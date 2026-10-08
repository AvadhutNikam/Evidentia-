import { useEffect, useState, useCallback } from 'react';
import L from 'leaflet';
import { useMap } from 'react-leaflet';
import { GeoCase } from '../../types';

export interface CasePoint {
  type: 'point';
  case: GeoCase;
  lat: number;
  lng: number;
}

export interface CaseCluster {
  type: 'cluster';
  id: string;
  lat: number;
  lng: number;
  count: number;
  cases: GeoCase[];
}

export type ClusterItem = CasePoint | CaseCluster;

const CLUSTER_PIXEL_RADIUS = 44;

export function useMarkerClusters(cases: GeoCase[]): ClusterItem[] {
  const map = useMap();
  const [items, setItems] = useState<ClusterItem[]>([]);

  const recompute = useCallback(() => {
    if (!map) return;

    // Filter to only cases with valid numeric latitude & longitude
    const validCases = (cases || []).filter(c => {
      if (!c) return false;
      const lat = typeof c.latitude === 'number' ? c.latitude : (typeof (c as any).lat === 'number' ? (c as any).lat : null);
      const lng = typeof c.longitude === 'number' ? c.longitude : (typeof (c as any).lng === 'number' ? (c as any).lng : null);
      return lat !== null && lng !== null && !isNaN(lat) && !isNaN(lng);
    });

    const points = validCases.map(c => {
      const lat = typeof c.latitude === 'number' ? c.latitude : (c as any).lat;
      const lng = typeof c.longitude === 'number' ? c.longitude : (c as any).lng;
      let containerPoint = { x: 0, y: 0 };
      try {
        containerPoint = map.latLngToContainerPoint(L.latLng(lat, lng));
      } catch (err) {
        console.warn('Invalid coordinate calculation:', lat, lng, err);
      }
      return {
        case: {
          ...c,
          latitude: lat,
          longitude: lng,
          crimeType: c.crimeType || 'Other',
          severity: c.severity || 'Medium',
          status: c.status || 'Active',
          location: c.location || 'India'
        },
        lat,
        lng,
        containerPoint,
      };
    });

    const visited = new Set<number>();
    const result: ClusterItem[] = [];

    for (let i = 0; i < points.length; i++) {
      if (visited.has(i)) continue;
      visited.add(i);
      const group = [points[i]];

      for (let j = i + 1; j < points.length; j++) {
        if (visited.has(j)) continue;
        const dx = points[i].containerPoint.x - points[j].containerPoint.x;
        const dy = points[i].containerPoint.y - points[j].containerPoint.y;
        if (Math.sqrt(dx * dx + dy * dy) <= CLUSTER_PIXEL_RADIUS) {
          visited.add(j);
          group.push(points[j]);
        }
      }

      if (group.length === 1) {
        result.push({
          type: 'point',
          case: group[0].case,
          lat: group[0].lat,
          lng: group[0].lng,
        });
      } else {
        const avgLat = group.reduce((sum, p) => sum + p.lat, 0) / group.length;
        const avgLng = group.reduce((sum, p) => sum + p.lng, 0) / group.length;
        result.push({
          type: 'cluster',
          id: `cluster-${group.map(p => p.case.id).join('-')}`,
          lat: avgLat,
          lng: avgLng,
          count: group.length,
          cases: group.map(p => p.case),
        });
      }
    }

    setItems(result);
  }, [map, cases]);

  useEffect(() => {
    recompute();
  }, [recompute]);

  useEffect(() => {
    if (!map) return;
    map.on('zoomend', recompute);
    map.on('moveend', recompute);
    return () => {
      map.off('zoomend', recompute);
      map.off('moveend', recompute);
    };
  }, [map, recompute]);

  return items;
}
