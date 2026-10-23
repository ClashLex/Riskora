import { BrowserRouter, Link, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { Activity, ChartNoAxesCombined, ChevronDown, CircleHelp, FlaskConical, LayoutDashboard, Menu, Radar, Settings2, ShieldCheck, Wallet, X } from 'lucide-react'
import { lazy, Suspense, useState } from 'react'
import { Badge, DemoBanner } from './components'
import { currencies } from './data'
import { StoreProvider, useStore } from './store'
import { ConnectedProvider, useConnected } from './connected/context'
import { useMockData } from './services/api'
import './index.css'

const Overview = lazy(() => import('./pages/Overview'))
const Portfolio = lazy(() => import('./pages/Portfolio'))
const Exposure = lazy(() => import('./pages/Exposure'))
const Stress = lazy(() => import('./pages/Stress'))
const Insights = lazy(() => import('./pages/Insights'))
const Settings = lazy(() => import('./pages/Settings'))
const ConnectedOverview = lazy(() => import('./connected/Overview'))
const ConnectedPortfolio = lazy(() => import('./connected/Portfolio'))
const ConnectedExposure = lazy(() => import('./connected/Exposure'))
const ConnectedStress = lazy(() => import('./connected/Stress'))
const ConnectedInsights = lazy(() => import('./connected/Insights'))
const ConnectedSettings = lazy(() => import('./connected/Settings'))

const nav = [ { to: '/', label: 'Overview', icon: LayoutDashboard }, { to: '/portfolio', label: 'Portfolio', icon: Wallet }, { to: '/exposure', label: 'Exposure analysis', icon: ChartNoAxesCombined }, { to: '/stress-test', label: 'Stress tests', icon: FlaskConical }, { to: '/insights', label: 'Risk insights', icon: Activity }, { to: '/settings', label: 'Settings', icon: Settings2 } ]
function Shell() {
  const { currency, setCurrency } = useStore()
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  const current = nav.find(n => n.to === pathname)?.label ?? 'Page not found'
  return useMockData ? <ShellContent current={current} currency={currency} setCurrency={setCurrency} open={open} setOpen={setOpen}/> : <ConnectedShell current={current} currency={currency} setCurrency={setCurrency} open={open} setOpen={setOpen}/>
}
type ShellProps = { current: string; currency: import('./types').Currency; setCurrency: (c: import('./types').Currency) => void; open: boolean; setOpen: (v: boolean) => void }
function ConnectedShell(props: ShellProps) { const connected = useConnected(); return <ShellContent {...props} connected={connected}/> }
function ShellContent({ current, currency, setCurrency, open, setOpen, connected }: ShellProps & { connected?: ReturnType<typeof useConnected> }) {
  return <div className="app-shell">
    {open && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setOpen(false)}/>}
    <aside className={`sidebar ${open ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Radar size={22}/></div><span>RISVANTA</span><button className="icon-btn mobile-close" aria-label="Close menu" onClick={() => setOpen(false)}><X size={20}/></button></div>
      <div className="workspace-label">WORKSPACE <ChevronDown size={13}/></div><div className="workspace-name"><span className="workspace-avatar">R</span><span>Demo workspace<small>Personal analysis</small></span></div>
      <p className="nav-label">ANALYZE</p><nav aria-label="Main navigation">{nav.slice(0, 5).map(item => <NavLink key={item.to} to={item.to} end={item.to === '/'} onClick={() => setOpen(false)} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><item.icon size={18}/>{item.label}</NavLink>)}</nav>
      <p className="nav-label tools-label">PREFERENCES</p><nav><NavLink to="/settings" onClick={() => setOpen(false)} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><Settings2 size={18}/>Settings</NavLink></nav>
      <div className="sidebar-bottom"><div className="sidebar-help"><CircleHelp size={18}/><div><strong>Built for clarity</strong><span>Explore your risk, not advice.</span></div></div><div className="sidebar-user"><span className="user-avatar">DU</span><span><strong>Demo user</strong><small>Local workspace</small></span><Badge>DEMO</Badge></div></div>
    </aside>
    <div className="main-area"><header className="topbar"><div className="topbar-left"><button className="icon-btn menu-btn" aria-label="Open menu" onClick={() => setOpen(true)}><Menu size={21}/></button><span className="breadcrumb">Workspace</span><span className="breadcrumb-sep">/</span><strong>{current}</strong></div><div className="topbar-right">{connected && <label className="currency-picker">Portfolio <select aria-label="Portfolio" value={connected.selected} onChange={e => connected.select(e.target.value)}>{connected.portfolios.length ? connected.portfolios.map(p => <option key={p.id} value={p.id}>{p.name}</option>) : <option value={connected.selected}>{connected.selected}</option>}</select></label>}<span className="sample-indicator"><span className="status-dot"/>{connected ? 'API · illustrative' : 'Sample data'}</span><label className="currency-picker">Base currency <select value={currency} onChange={e => setCurrency(e.target.value as typeof currency)}>{currencies.map(c => <option key={c}>{c}</option>)}</select></label><div className="top-avatar" title="Demo user">DU</div></div></header><main className="content"><DemoBanner/>{connected?.loading ? <div role="status" className="card">Loading portfolio from the analysis service…</div> : connected?.error ? <div role="alert" className="card"><h2>We couldn’t connect to the analysis service.</h2><p>{connected.error}</p><button className="btn secondary" onClick={connected.retry}>Retry</button><p className="card-note">No local data has been substituted. Set VITE_USE_MOCK_DATA=true and restart the frontend for offline demo mode.</p></div> : <Suspense fallback={<div className="card" role="status">Loading workspace view…</div>}><Routes><Route path="/" element={connected ? <ConnectedOverview/> : <Overview/>}/><Route path="/portfolio" element={connected ? <ConnectedPortfolio/> : <Portfolio/>}/><Route path="/exposure" element={connected ? <ConnectedExposure/> : <Exposure/>}/><Route path="/stress-test" element={connected ? <ConnectedStress/> : <Stress/>}/><Route path="/insights" element={connected ? <ConnectedInsights/> : <Insights/>}/><Route path="/settings" element={connected ? <ConnectedSettings/> : <Settings/>}/><Route path="*" element={<div className="not-found"><ShieldCheck size={38}/><h1>This page is out of range.</h1><p>We couldn’t find that workspace view.</p><Link className="btn primary" to="/">Back to overview</Link></div>}/></Routes></Suspense>}<footer>RISVANTA <span>•</span> See beyond the returns. <span className="footer-right">Illustrative analysis · Not investment advice</span></footer></main></div>
  </div>
}
export default function App() { return <BrowserRouter><StoreProvider>{useMockData ? <Shell/> : <ConnectedProvider><Shell/></ConnectedProvider>}</StoreProvider></BrowserRouter> }
