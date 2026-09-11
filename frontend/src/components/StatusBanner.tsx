/**
 * How failures and staleness are shown.
 *
 * The spec requires that a member is told when the list cannot be confirmed
 * current, and that a change which failed is never presented as saved. That
 * makes this component part of the contract, not decoration.
 */

import { errorMessage, isOffline } from '../api/errors'

export function StatusBanner({
  error,
  onRetry,
}: {
  error: unknown
  onRetry?: () => void
}) {
  if (!error) return null

  const offline = isOffline(error)

  return (
    <div className="banner banner--error" role="alert" data-testid="status-banner">
      <span>
        {offline ? 'Offline — this list may be out of date. ' : ''}
        {errorMessage(error)}
      </span>
      {onRetry && (
        <button type="button" className="banner__action" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  )
}
