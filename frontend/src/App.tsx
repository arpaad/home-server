import { NavLink, Route, Routes } from 'react-router'

import { useMembers } from './api/queries'
import { MemberPicker } from './components/MemberPicker'
import { useCurrentMember } from './member/MemberContext'
import { dismissNotice, useNotices } from './net/notices'
import { AddPage } from './pages/AddPage'
import { CataloguePage } from './pages/CataloguePage'
import { ListPage } from './pages/ListPage'
import { ManagePage } from './pages/ManagePage'

/**
 * Four routes, no nesting, no guards. The list is the default and every
 * other route has a way back to it, because on a phone the back gesture is
 * how people close things.
 */
export default function App() {
  const { memberId, setMemberId } = useCurrentMember()
  const members = useMembers()
  const notices = useNotices()

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__title">
          <h1>
            <NavLink to="/" className="app__home">
              H.O.M.E.
            </NavLink>
          </h1>
          <nav className="app__nav" aria-label="Sections">
            <NavLink to="/" end className="app__navlink">
              List
            </NavLink>
            <NavLink to="/catalogue" className="app__navlink" data-testid="nav-catalogue">
              Catalogue
            </NavLink>
            <NavLink to="/manage" className="app__navlink" data-testid="nav-manage">
              Manage
            </NavLink>
          </nav>
        </div>
        <MemberPicker members={members.data ?? []} memberId={memberId} onChange={setMemberId} />
      </header>

      {/* What did not go through, and why. Dismissible; never silent. */}
      {notices.map((notice) => (
        <div key={notice.id} className="banner banner--error" role="alert" data-testid="sync-notice">
          <span>{notice.text}</span>
          <button type="button" className="banner__action" onClick={() => dismissNotice(notice.id)}>
            Dismiss
          </button>
        </div>
      ))}

      <Routes>
        <Route path="/" element={<ListPage />} />
        <Route path="/add" element={<AddPage />} />
        <Route path="/manage" element={<ManagePage />} />
        <Route path="/catalogue" element={<CataloguePage />} />
        <Route path="*" element={<ListPage />} />
      </Routes>

      <footer className="app__footer">
        On the household network only — no login, so keep it off the internet.
      </footer>
    </div>
  )
}
