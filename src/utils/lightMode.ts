/**
 * Station Light Mode Engine
 * 
 * Automatically detects low-resource station hardware and slow rural networks:
 * - RAM <= 4 GB (navigator.deviceMemory)
 * - CPU cores <= 4 (navigator.hardwareConcurrency)
 * - Slow cellular or Data Saver active (navigator.connection.saveData or 2G/3G)
 * 
 * When active, eliminates expensive CSS blurs, animation loops, D3 physics
 * simulation, and interactive Leaflet map tile rendering.
 */

const STORAGE_KEY = 'evidentia_light_mode';

export interface DeviceResourceProfile {
  deviceMemoryGB: number | null;
  hardwareConcurrency: number | null;
  saveData: boolean;
  effectiveNetworkType: string | null;
  isAutoRecommended: boolean;
}

export function detectDeviceResourceProfile(): DeviceResourceProfile {
  if (typeof window === 'undefined') {
    return {
      deviceMemoryGB: null,
      hardwareConcurrency: null,
      saveData: false,
      effectiveNetworkType: null,
      isAutoRecommended: false,
    };
  }

  const nav = navigator as any;
  const deviceMemoryGB = typeof nav.deviceMemory === 'number' ? nav.deviceMemory : null;
  const hardwareConcurrency = typeof nav.hardwareConcurrency === 'number' ? nav.hardwareConcurrency : null;
  const connection = nav.connection || nav.mozConnection || nav.webkitConnection;
  const saveData = connection?.saveData === true;
  const effectiveNetworkType = connection?.effectiveType || null;

  // Auto-recommend Light Mode if old station PC or slow connection
  const isLowRam = deviceMemoryGB !== null && deviceMemoryGB <= 4;
  const isLowCpu = hardwareConcurrency !== null && hardwareConcurrency <= 4;
  const isSlowNet = saveData || effectiveNetworkType === 'slow-2g' || effectiveNetworkType === '2g' || effectiveNetworkType === '3g';

  const isAutoRecommended = Boolean(isLowRam || isLowCpu || isSlowNet);

  return {
    deviceMemoryGB,
    hardwareConcurrency,
    saveData,
    effectiveNetworkType,
    isAutoRecommended,
  };
}

export function isLightMode(): boolean {
  if (typeof window === 'undefined') return false;
  
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved !== null) {
    return saved === 'true';
  }

  // Default to auto-detected recommendation if not explicitly overridden by user
  return detectDeviceResourceProfile().isAutoRecommended;
}

export function setLightMode(enabled: boolean): void {
  if (typeof window === 'undefined') return;
  
  localStorage.setItem(STORAGE_KEY, enabled ? 'true' : 'false');
  applyLightModeClass(enabled);

  window.dispatchEvent(
    new CustomEvent('evidentia:light-mode-changed', {
      detail: { enabled },
    })
  );
}

export function toggleLightMode(): boolean {
  const next = !isLightMode();
  setLightMode(next);
  return next;
}

export function applyLightModeClass(enabled: boolean): void {
  if (typeof document === 'undefined') return;
  if (enabled) {
    document.documentElement.classList.add('light-hardware-mode');
  } else {
    document.documentElement.classList.remove('light-hardware-mode');
  }
}

// Initialize on boot
if (typeof window !== 'undefined') {
  applyLightModeClass(isLightMode());
}

