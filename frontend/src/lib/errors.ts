import axios from 'axios';
import type { ApiError } from '@/types';

/**
 * Extract a user-facing message from a caught error, preferring the
 * backend's `error.message` field when the error came from an API call.
 *
 * Backend error responses are shaped `{ error: { code, message } }`
 * (see `backend/app/exceptions.py`), not a bare `detail` string.
 */
export function getApiErrorMessage(
  error: unknown,
  fallback = 'Something went wrong. Please try again.',
): string {
  if (axios.isAxiosError<ApiError>(error)) {
    return error.response?.data?.error?.message ?? error.message ?? fallback;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}
