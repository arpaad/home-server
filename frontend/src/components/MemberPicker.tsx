/** Choosing who is shopping. Identification, not a login. */

import type { Member } from '../api/types'

export function MemberPicker({
  members,
  memberId,
  onChange,
}: {
  members: Member[]
  memberId: string | null
  onChange: (id: string) => void
}) {
  return (
    <label className="member-picker">
      <span className="member-picker__label">Shopping as</span>
      <select
        data-testid="member-picker"
        value={memberId ?? ''}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="" disabled>
          Choose…
        </option>
        {members.map((member) => (
          <option key={member.id} value={member.id}>
            {member.name}
          </option>
        ))}
      </select>
    </label>
  )
}
