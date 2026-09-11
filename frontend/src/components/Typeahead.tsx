/**
 * Suggestions while typing an item name.
 *
 * Two rules from the spec shape this. Suggestions are never required: an
 * unfamiliar name can always be added, and the add button is never disabled
 * by an outstanding suggestion request. And choosing a suggestion is an
 * explicit act — typing the full name of something known does not silently
 * apply its stores.
 */

import { useEffect, useRef, useState } from 'react'

import { api } from '../api/client'
import type { CatalogueEntry } from '../api/types'

const DEBOUNCE_MS = 150

export function Typeahead({
  value,
  onChange,
  onChoose,
  inputTestId,
}: {
  value: string
  onChange: (value: string) => void
  onChoose: (entry: CatalogueEntry) => void
  inputTestId: string
}) {
  const [suggestions, setSuggestions] = useState<CatalogueEntry[]>([])
  const [open, setOpen] = useState(false)
  const controller = useRef<AbortController | null>(null)

  const prefix = value.trim()

  useEffect(() => {
    controller.current?.abort()
    if (prefix === '') return

    const own = new AbortController()
    controller.current = own
    const timer = window.setTimeout(() => {
      api
        .suggest(prefix, own.signal)
        .then((entries) => {
          if (!own.signal.aborted) setSuggestions(entries)
        })
        .catch(() => {
          // A failed suggestion request must not get in the way of adding.
          if (!own.signal.aborted) setSuggestions([])
        })
    }, DEBOUNCE_MS)

    return () => {
      window.clearTimeout(timer)
      own.abort()
    }
  }, [prefix])

  const choose = (entry: CatalogueEntry) => {
    onChoose(entry)
    setOpen(false)
    setSuggestions([])
  }

  // Derived, not stored: an empty box shows nothing whatever the last
  // request returned.
  const visible = open && prefix !== '' && suggestions.length > 0

  return (
    <div className="typeahead">
      <input
        data-testid={inputTestId}
        className="item-form__name"
        placeholder="What do we need?"
        value={value}
        autoComplete="off"
        autoFocus
        onChange={(event) => {
          onChange(event.target.value)
          setOpen(true)
          if (event.target.value.trim() === '') setSuggestions([])
        }}
        onFocus={() => setOpen(true)}
        // Delay so a tap on a suggestion lands before the list closes.
        onBlur={() => window.setTimeout(() => setOpen(false), 120)}
        required
      />
      {visible && (
        <ul className="typeahead__list" role="listbox" data-testid="suggestions">
          {suggestions.map((entry) => (
            <li key={entry.id}>
              <button
                type="button"
                role="option"
                aria-selected={false}
                className="typeahead__option"
                data-testid={`suggest-${entry.name}`}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(entry)}
              >
                <span className="typeahead__icon" aria-hidden="true">
                  {entry.category?.icon ?? '·'}
                </span>
                <span className="typeahead__name">{entry.name}</span>
                <span className="typeahead__meta">
                  {entry.category?.name ?? 'uncategorised'}
                  {entry.stores.length > 0 && ` · ${entry.stores.map((s) => s.name).join(', ')}`}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
