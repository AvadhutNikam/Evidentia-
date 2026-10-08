import { Marker, Popup, useMap } from 'react-leaflet';
import { ClusterItem } from './useMarkerClusters';
import { createCaseIcon, createClusterIcon } from './mapConfig';
import { CasePopup } from './CasePopup';

interface CaseMarkerProps {
  item: ClusterItem;
}

export function CaseMarker({ item }: CaseMarkerProps) {
  const map = useMap();

  if (item.type === 'cluster') {
    return (
      <Marker
        position={[item.lat, item.lng]}
        icon={createClusterIcon(item.count)}
        eventHandlers={{
          click: () => {
            map.setView([item.lat, item.lng], Math.min(map.getZoom() + 2, 16), { animate: true });
          },
        }}
      />
    );
  }

  const crimeType = item.case.crimeType || 'Other';
  const severity = item.case.severity || 'Medium';

  return (
    <Marker position={[item.lat, item.lng]} icon={createCaseIcon(crimeType, severity)}>
      <Popup className="evidentia-popup" closeButton minWidth={240} maxWidth={280}>
        <CasePopup geoCase={item.case} />
      </Popup>
    </Marker>
  );
}
