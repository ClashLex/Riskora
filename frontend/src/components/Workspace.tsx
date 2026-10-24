import type { ReactNode } from 'react'
import { IconChartLine, IconRefresh } from '@tabler/icons-react'
import type { Page } from '../domain'
import { pages, pageHash } from '../navigation'
import PillNav from './PillNav'

const navItems = pages.map(({ name, icon: Icon }) => ({
  label: name === 'Evidence' ? 'Supporting signals' : name,
  href: pageHash(name),
  ariaLabel: name === 'Evidence' ? 'Supporting signals' : name,
  icon: <Icon size={18} stroke={1.8} aria-hidden="true" />,
}))

export function Workspace({
  page,
  navigate,
  refresh,
  busy,
  children,
}: {
  page: Page
  navigate: (page: Page) => void
  refresh: () => void
  busy: boolean
  children: ReactNode
}) {
  const current = pages.find((item) => item.name === page)!

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
      <div className="workspace-topbar">
        <a
          className="brand"
          href="#overview"
          onClick={(event) => {
            if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return
            event.preventDefault()
            navigate('Overview')
          }}
        >
          <IconChartLine size={25} stroke={1.7} aria-hidden="true" />
          <span>
            Riskora<small>Disclosed holdings research</small>
          </span>
        </a>
        <div className="workspace-nav-wrap">
          <PillNav
            items={navItems}
            activeHref={pageHash(page)}
            ariaLabel="Main navigation"
            theme="light"
            layout="joined"
            size="sm"
            surface="solid"
            hoverEffect="glide"
            indicator="pill"
            intro={false}
            onItemClick={(_, index, event) => {
              if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return
              event.preventDefault()
              navigate(pages[index].name)
            }}
          />
        </div>
      </div>
      <main id="main-content" tabIndex={-1} className="main-area">
        <header className="page-header">
          <div className="page-header-copy">
            <h1>{current.title}</h1>
            <p>{current.description}</p>
          </div>
          <div className="header-actions">
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
    </div>
  )
}
