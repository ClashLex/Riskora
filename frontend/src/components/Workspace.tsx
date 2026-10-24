import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { IconChartLine, IconMenu2, IconRefresh, IconSearch, IconX } from '@tabler/icons-react'
import type { Page, Fund } from '../domain'
import { dateLabel } from '../domain'
import { pages, pageHash } from '../navigation'

function FundList({
  funds,
  fundId,
  select,
}: {
  funds: Fund[]
  fundId: string
  select: (id: string) => void
}) {
  const [query, setQuery] = useState('')
  const [source, setSource] = useState('all')
  const filtered = funds.filter(
    (fund) =>
      (source === 'all' || fund.source_kind === source) &&
      `${fund.name} ${fund.amc}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()),
  )
  if (!funds.length)
    return <p className="sidebar-empty">No funds yet. Import disclosures to add one.</p>
  return (
    <>
      <label className="sidebar-search">
        <span>Find a fund</span>
        <span className="search-field">
          <IconSearch size={17} aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Name or AMC"
          />
        </span>
      </label>
      <label className="source-filter">
        Data source
        <select value={source} onChange={(event) => setSource(event.target.value)}>
          <option value="all">All data</option>
          <option value="user_import">Imported</option>
          <option value="synthetic">Synthetic sample</option>
        </select>
      </label>
      <ul className="fund-list">
        {filtered.map((fund) => (
          <li key={fund.id}>
            <button data-selected={fund.id === fundId || undefined} onClick={() => select(fund.id)}>
              <strong>{fund.name}</strong>
              <span>
                {fund.source_kind === 'synthetic' ? 'Sample · ' : ''}
                {fund.observations} disclosures
              </span>
              <span>Report {dateLabel(fund.latest_report_date)}</span>
            </button>
          </li>
        ))}
      </ul>
      {!filtered.length && <p className="sidebar-empty">No funds match these filters.</p>}
    </>
  )
}
export function Workspace({
  page,
  navigate,
  funds,
  fundId,
  selectFund,
  refresh,
  busy,
  children,
}: {
  page: Page
  navigate: (page: Page) => void
  funds: Fund[]
  fundId: string
  selectFund: (id: string) => void
  refresh: () => void
  busy: boolean
  children: ReactNode
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const drawerToggle = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)
  const current = pages.find((item) => item.name === page)!
  function close() {
    dialog.current?.close()
    setOpen(false)
    drawerToggle.current?.focus()
  }
  function select(id: string) {
    selectFund(id)
    if (open) close()
    navigate('Fund explorer')
  }
  useEffect(() => {
    const onResize = () => {
      if (window.innerWidth > 760 && dialog.current?.open) {
        dialog.current.close()
        setOpen(false)
      }
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  return (
    <div className="workspace">
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault()
          document.getElementById('main-content')?.focus()
        }}
      >
        Skip to content
      </a>
      <aside className="sidebar" aria-label="Research workspace">
        <a
          className="brand"
          href="#overview"
          onClick={(event) => {
            event.preventDefault()
            navigate('Overview')
          }}
        >
          <IconChartLine size={27} aria-hidden="true" />
          <span>
            Riskora<small>Disclosed holdings research</small>
          </span>
        </a>
        <nav className="main-nav" aria-label="Main navigation">
          {pages.map(({ name, short, icon: Icon }) => (
            <a
              href={pageHash(name)}
              key={name}
              aria-label={name === 'Evidence' ? 'Supporting signals' : name}
              aria-current={page === name ? 'page' : undefined}
              onClick={(event) => {
                if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return
                event.preventDefault()
                navigate(name)
              }}
            >
              <Icon size={20} stroke={1.8} aria-hidden="true" />
              <span className="nav-full">{name === 'Evidence' ? 'Supporting signals' : name}</span>
              <span className="nav-short" aria-hidden="true">
                {short}
              </span>
            </a>
          ))}
        </nav>
        <div className="desktop-funds">
          <h2>
            Fund library <span>{funds.length}</span>
          </h2>
          <FundList funds={funds} fundId={fundId} select={select} />
        </div>
      </aside>
      <main id="main-content" tabIndex={-1} className="main-area">
        <header className="page-header">
          <div>
            <h1>{current.title}</h1>
          </div>
          <div className="header-actions">
            <button
              ref={drawerToggle}
              className="icon-button drawer-toggle"
              aria-label="Open fund library"
              aria-haspopup="dialog"
              aria-expanded={open}
              onClick={() => {
                dialog.current?.showModal()
                setOpen(true)
              }}
            >
              <IconMenu2 size={21} aria-hidden="true" />
            </button>
            <button
              className="icon-button"
              aria-label="Refresh workspace data"
              title="Refresh data"
              disabled={busy}
              onClick={refresh}
            >
              <IconRefresh size={19} aria-hidden="true" />
            </button>
          </div>
        </header>
        <div className="content">{children}</div>
      </main>
      <dialog
        ref={dialog}
        className="fund-drawer"
        aria-labelledby="fund-drawer-title"
        onKeyDown={(event) => {
          if (event.key !== 'Tab') return
          const controls = Array.from(
            event.currentTarget.querySelectorAll<HTMLElement>(
              'button:not(:disabled), input:not(:disabled), select:not(:disabled), a[href]',
            ),
          )
          const first = controls[0],
            last = controls[controls.length - 1]
          if (event.shiftKey && document.activeElement === first) {
            event.preventDefault()
            last?.focus()
          }
          if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault()
            first?.focus()
          }
        }}
        onCancel={() => setOpen(false)}
        onClose={() => {
          setOpen(false)
          drawerToggle.current?.focus()
        }}
        onClick={(event) => {
          if (event.target === event.currentTarget) {
            const rect = event.currentTarget.getBoundingClientRect()
            if (
              event.clientX < rect.left ||
              event.clientX > rect.right ||
              event.clientY < rect.top ||
              event.clientY > rect.bottom
            )
              close()
          }
        }}
      >
        <div className="drawer-heading">
          <h2 id="fund-drawer-title">Fund library</h2>
          <button className="icon-button" aria-label="Close fund library" onClick={close}>
            <IconX size={20} aria-hidden="true" />
          </button>
        </div>
        {open && <FundList funds={funds} fundId={fundId} select={select} />}
      </dialog>
    </div>
  )
}
