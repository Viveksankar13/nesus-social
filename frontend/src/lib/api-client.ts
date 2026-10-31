/**
 * Nexus Social API Client
 * =======================
 * Fetch wrapper featuring:
 * - In-memory access token storage (no localStorage persistence for security)
 * - Automatic Authorization header injection
 * - Credentials: "include" for httpOnly rotating refresh token cookie
 * - Silent refresh interceptor on 401 with concurrency deduplication
 * - Custom ApiClientError parsing
 */

export class ApiClientError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.data = data;
  }
}

let inMemoryAccessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function getAccessToken(): string | null {
  return inMemoryAccessToken;
}

export function setAccessToken(token: string | null): void {
  inMemoryAccessToken = token;
}

export type QueryParamValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | Array<string | number | boolean>;

export type QueryParams = Record<string, QueryParamValue>;

export interface RequestOptions extends RequestInit {
  _retry?: boolean;
  params?: QueryParams;
}

export function buildUrlWithParams(url: string, params?: QueryParams): string {
  if (!params) return url;
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item !== undefined && item !== null) {
          searchParams.append(key, String(item));
        }
      }
    } else {
      searchParams.append(key, String(value));
    }
  }
  const queryString = searchParams.toString();
  if (!queryString) return url;
  return url.includes("?") ? `${url}&${queryString}` : `${url}?${queryString}`;
}

/**
 * Execute silent token refresh.
 * Deduplicates concurrent 401s so only a single /auth/refresh call is made.
 */
async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const response = await fetch("/api/v1/auth/refresh", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        setAccessToken(null);
        return null;
      }

      const data = await response.json();
      const newToken = data.access_token as string;
      setAccessToken(newToken);
      return newToken;
    } catch {
      setAccessToken(null);
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * Main fetch wrapper with automatic authentication & silent refresh.
 */
export async function apiFetch<T = unknown>(
  url: string,
  options: RequestOptions = {}
): Promise<T> {
  const normalizedUrl = url.startsWith("/") ? url : `/${url}`;
  let fullUrl = normalizedUrl.startsWith("/api")
    ? normalizedUrl
    : `/api/v1${normalizedUrl}`;

  if (options.params) {
    fullUrl = buildUrlWithParams(fullUrl, options.params);
  }

  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const token = getAccessToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const fetchInit = { ...options };
  delete fetchInit.params;
  delete fetchInit._retry;
  const response = await fetch(fullUrl, {
    ...fetchInit,
    headers,
    credentials: "include",
  });

  // Handle 401 Unauthorized via silent refresh
  if (response.status === 401 && !options._retry && !url.includes("/auth/")) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers.set("Authorization", `Bearer ${newToken}`);
      return apiFetch<T>(url, {
        ...options,
        headers,
        _retry: true,
      });
    }
  }

  // Handle successful empty response (e.g. 204 No Content)
  if (response.status === 204) {
    return {} as T;
  }

  let responseData: unknown = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      responseData = await response.json();
    } catch {
      responseData = null;
    }
  } else {
    responseData = await response.text();
  }

  if (!response.ok) {
    let errorMessage = `Request failed with status ${response.status}`;
    if (typeof responseData === "object" && responseData !== null) {
      const dataObj = responseData as Record<string, unknown>;
      if (typeof dataObj.detail === "string") {
        errorMessage = dataObj.detail;
      } else if (Array.isArray(dataObj.detail) && dataObj.detail.length > 0) {
        const firstErr = dataObj.detail[0] as { msg?: string };
        errorMessage = firstErr.msg || errorMessage;
      }
    }
    throw new ApiClientError(errorMessage, response.status, responseData);
  }

  return responseData as T;
}

function resolveOptions(
  paramsOrOptions?: QueryParams | RequestOptions,
  maybeOptions?: RequestOptions
): RequestOptions {
  if (!paramsOrOptions) {
    return maybeOptions || {};
  }

  const hasRequestInitKeys =
    "headers" in paramsOrOptions ||
    "signal" in paramsOrOptions ||
    "params" in paramsOrOptions ||
    "cache" in paramsOrOptions ||
    "credentials" in paramsOrOptions ||
    "mode" in paramsOrOptions ||
    "body" in paramsOrOptions ||
    "_retry" in paramsOrOptions;

  if (hasRequestInitKeys) {
    return { ...(paramsOrOptions as RequestOptions), ...maybeOptions };
  }

  return {
    ...maybeOptions,
    params: paramsOrOptions as QueryParams,
  };
}

export const apiClient = {
  get: <T>(
    url: string,
    paramsOrOptions?: QueryParams | RequestOptions,
    options?: RequestOptions
  ) =>
    apiFetch<T>(url, {
      ...resolveOptions(paramsOrOptions, options),
      method: "GET",
    }),

  post: <T>(url: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(url, {
      ...options,
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),

  put: <T>(url: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(url, {
      ...options,
      method: "PUT",
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),

  patch: <T>(url: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(url, {
      ...options,
      method: "PATCH",
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),

  delete: <T>(
    url: string,
    paramsOrOptions?: QueryParams | RequestOptions,
    options?: RequestOptions
  ) =>
    apiFetch<T>(url, {
      ...resolveOptions(paramsOrOptions, options),
      method: "DELETE",
    }),
};
