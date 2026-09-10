/** Turning any thrown value into something a member can read. */

import { ApiError, OfflineError } from './client'

export function errorMessage(error: unknown): string {
  if (error instanceof OfflineError) return error.message
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return 'Something went wrong.'
}

export function isOffline(error: unknown): boolean {
  return error instanceof OfflineError
}
