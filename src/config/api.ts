/**
 * Central API & Environment Configuration
 * 
 * Unifies VITE_API_URL, token storage keys, and explicit Demo Mode handling
 * across the entire Evidentia application.
 */

function resolveDefaultApiBase(): string {
  const envUrl = typeof import.meta !== 'undefined' ? (import.meta as any).env?.VITE_API_URL : undefined;
  if (envUrl) {
    return String(envUrl).replace(/\/+$/, '');
  }
  if (typeof window !== 'undefined' && window.location) {
    const host = window.location.hostname;
    if (host === 'localhost') {
      return 'http://localhost:8000';
    }
    if (host === '127.0.0.1') {
      return 'http://127.0.0.1:8000';
    }
    if (host) {
      return `${window.location.protocol}//${host}:8000`;
    }
  }
  return 'http://127.0.0.1:8000';
}

// Single source of truth for the backend API base URL
export const API_BASE: string = resolveDefaultApiBase();
export const API_BASE_URL: string = API_BASE;

// Storage keys
export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'evidentia_access_token',
  REFRESH_TOKEN: 'evidentia_refresh_token',
  USER: 'evidentia_user',
  DEMO_MODE: 'evidentia_demo_mode',
} as const;

/**
 * Returns whether explicit Demo Mode (mock data fallback) is active.
 * Default is FALSE (live backend required; backend errors trigger error banner).
 */
export function isDemoMode(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem(STORAGE_KEYS.DEMO_MODE) === 'true';
}

/**
 * Sets explicit Demo Mode and dispatches a notification event.
 */
export function setDemoMode(enabled: boolean): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEYS.DEMO_MODE, enabled ? 'true' : 'false');
  window.dispatchEvent(
    new CustomEvent('evidentia:demo-mode-changed', {
      detail: { enabled },
    })
  );
}

/**
 * Toggles explicit Demo Mode and returns the new state.
 */
export function toggleDemoMode(): boolean {
  const next = !isDemoMode();
  setDemoMode(next);
  return next;
}
