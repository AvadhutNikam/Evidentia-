/**
 * Shared API Client for Evidentia-AI
 * 
 * Features:
 * - Centralized request execution using unified API_BASE
 * - Automatic Bearer token attachment from localStorage
 * - Seamless 401 handling with automatic token refresh (/auth/refresh)
 * - Automatic logout and auth event dispatch on refresh expiration
 * - Strict Mock Fallback isolation: mock fallbacks only active when isDemoMode() === true
 * - Global error event dispatch for UI Error Banner notification
 */

import { API_BASE, STORAGE_KEYS, isDemoMode } from '../config/api.ts';

export interface ApiRequestOptions extends RequestInit {
  fallback?: any;           // Explicit mock data to use ONLY when Demo Mode is active
  skipAuth?: boolean;       // Bypass token header (e.g., login or public endpoints)
  skipRefresh?: boolean;    // Guard against infinite refresh loops
  suppressBanner?: boolean; // Do not emit error banner notification event
}

export interface ApiErrorEventDetail {
  message: string;
  status: number;
  endpoint: string;
  timestamp: number;
}

export class ApiError extends Error {
  status: number;
  endpoint: string;

  constructor(message: string, status: number = 0, endpoint: string = '') {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.endpoint = endpoint;
  }
}

/**
 * Dispatches a global API error event for the GlobalErrorBanner component.
 */
export function dispatchApiError(error: Omit<ApiErrorEventDetail, 'timestamp'>): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(
    new CustomEvent<ApiErrorEventDetail>('evidentia:api-error', {
      detail: {
        ...error,
        timestamp: Date.now(),
      },
    })
  );
}

/**
 * Core shared request function for all Evidentia API interactions.
 */
export async function apiRequest<T = any>(
  endpoint: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  const url =
    endpoint.startsWith('http://') || endpoint.startsWith('https://')
      ? endpoint
      : `${API_BASE}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  // Configure headers
  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  // Attach access token unless skipped
  if (!options.skipAuth) {
    const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Handle 401 Unauthorized via Refresh Token
    if (response.status === 401 && !options.skipRefresh) {
      const refreshToken = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);

      if (refreshToken) {
        try {
          const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken }),
          });

          if (refreshRes.ok) {
            const tokenData = await refreshRes.json();
            if (tokenData.access_token) {
              localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, tokenData.access_token);
              if (tokenData.refresh_token) {
                localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, tokenData.refresh_token);
              }
              if (tokenData.user) {
                localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(tokenData.user));
              }

              // Notify AuthContext of updated token
              window.dispatchEvent(
                new CustomEvent('evidentia:token-refreshed', { detail: tokenData })
              );

              // Retry original request with newly acquired access token
              const retryHeaders = new Headers(options.headers || {});
              if (!retryHeaders.has('Content-Type') && !(options.body instanceof FormData)) {
                retryHeaders.set('Content-Type', 'application/json');
              }
              retryHeaders.set('Authorization', `Bearer ${tokenData.access_token}`);

              return await apiRequest<T>(endpoint, {
                ...options,
                headers: retryHeaders,
                skipRefresh: true,
              });
            }
          }
        } catch (refreshErr) {
          console.warn('[ApiClient] Token refresh attempt failed:', refreshErr);
        }
      }

      // Refresh failed or no refresh token available: clear authentication session
      localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
      localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
      localStorage.removeItem(STORAGE_KEYS.USER);

      window.dispatchEvent(new CustomEvent('evidentia:auth-unauthorized'));

      const sessionErrMessage = 'Authentication session expired. Please log in again.';
      if (!options.suppressBanner) {
        dispatchApiError({
          message: sessionErrMessage,
          status: 401,
          endpoint,
        });
      }

      if (isDemoMode() && options.fallback !== undefined) {
        return options.fallback as T;
      }

      throw new ApiError(sessionErrMessage, 401, endpoint);
    }

    // Handle non-OK HTTP responses
    if (!response.ok) {
      let errorMessage = `HTTP ${response.status} (${response.statusText})`;
      try {
        const errorJson = await response.json();
        errorMessage = errorJson.detail || errorJson.message || JSON.stringify(errorJson);
      } catch {
        const errorText = await response.text().catch(() => '');
        if (errorText) errorMessage = errorText;
      }

      // If Demo Mode is explicitly enabled and a fallback exists, serve it
      if (isDemoMode() && options.fallback !== undefined) {
        console.info(
          `[Demo Mode Active] Endpoint ${endpoint} returned ${response.status}; using mock fallback.`
        );
        return options.fallback as T;
      }

      // In Live Backend Mode: dispatch global error banner event and throw
      if (!options.suppressBanner && !isDemoMode()) {
        dispatchApiError({
          message: errorMessage,
          status: response.status,
          endpoint,
        });
      }

      throw new ApiError(errorMessage, response.status, endpoint);
    }

    // Parse successful response body
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('evidentia:api-success', { detail: { endpoint } }));
    }

    if (response.status === 204) {
      return null as T;
    }

    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      return (await response.json()) as T;
    }
    if (
      contentType.includes('application/pdf') ||
      contentType.includes('application/octet-stream')
    ) {
      return (await response.blob()) as unknown as T;
    }

    return (await response.text()) as unknown as T;
  } catch (err: any) {
    // If the error is already an ApiError from above, rethrow
    if (err instanceof ApiError) {
      throw err;
    }

    // Network / Connection Error (e.g. backend offline or unreachable)
    const netMessage =
      err?.message === 'Failed to fetch' || err?.name === 'TypeError'
        ? `Backend unreachable at ${API_BASE}. Ensure server is running.`
        : err?.message || 'Network request failed';

    if (isDemoMode() && options.fallback !== undefined) {
      console.info(
        `[Demo Mode Active] Network error calling ${endpoint}; using mock fallback.`
      );
      return options.fallback as T;
    }

    if (!options.suppressBanner && !isDemoMode()) {
      dispatchApiError({
        message: netMessage,
        status: 0,
        endpoint,
      });
    }

    throw new ApiError(netMessage, 0, endpoint);
  }
}
