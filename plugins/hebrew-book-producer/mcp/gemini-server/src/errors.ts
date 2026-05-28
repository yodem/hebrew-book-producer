/**
 * Structured error codes returned by tools. The MCP server surfaces these as
 * tool-call results with `isError: true` so the calling skill/agent can branch
 * on the `code` field rather than parsing prose.
 */
export type ErrorCode =
  | 'no_credentials'
  | 'api_error'
  | 'transient'
  | 'validation'
  | 'bundle_load_failed';

export interface StructuredError {
  code: ErrorCode;
  message: string;
  details?: Record<string, unknown>;
}

export function noCredentials(): StructuredError {
  return {
    code: 'no_credentials',
    message:
      'No Gemini API key found. Set GOOGLE_API_KEY (or GEMINI_API_KEY) in your environment, or add it as "google_api_key" in .book-producer/secrets.json.',
  };
}

export function apiError(message: string, details?: Record<string, unknown>): StructuredError {
  return { code: 'api_error', message, details };
}

export function transient(message: string, details?: Record<string, unknown>): StructuredError {
  return { code: 'transient', message, details };
}

export function validation(message: string, details?: Record<string, unknown>): StructuredError {
  return { code: 'validation', message, details };
}

export function bundleLoadFailed(message: string, details?: Record<string, unknown>): StructuredError {
  return { code: 'bundle_load_failed', message, details };
}

export function toToolResult(err: StructuredError): {
  isError: true;
  content: Array<{ type: 'text'; text: string }>;
} {
  return {
    isError: true,
    content: [
      {
        type: 'text',
        text: JSON.stringify(err),
      },
    ],
  };
}

export function isRetryable(httpStatus?: number, errCode?: string): boolean {
  if (httpStatus === undefined && errCode === undefined) return false;
  if (httpStatus !== undefined) {
    if (httpStatus >= 500 && httpStatus < 600) return true;
    if (httpStatus === 429) return true;
  }
  if (errCode) {
    const transientCodes = new Set([
      'ECONNRESET',
      'ETIMEDOUT',
      'ENOTFOUND',
      'EAI_AGAIN',
      'ECONNREFUSED',
      'EPIPE',
    ]);
    if (transientCodes.has(errCode)) return true;
  }
  return false;
}
