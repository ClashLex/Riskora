import { ArrowDownRight, ArrowUpRight, ArrowRight, Info, Plus, Search, X } from 'lucide-react'
import type { PropsWithChildren, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import * as Dialog from '@radix-ui/react-dialog'
import type { Currency } from './types'

export const money = (n: number, currency: Currency, compact = false) => new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: compact ? 0 : 2, notation: compact ? 'compact' : 'standard' }).format(n)
export const percent = (n: number) => new Intl.NumberFormat('en-US', { style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(n)
export function Card({ children, className = '' }: PropsWithChildren<{ className?: string }>) { return <section className={`card ${className}`}>{children}</section> }
export function Badge({ children, tone = 'neutral' }: PropsWithChildren<{ tone?: string }>) { return <span className={`badge badge-${tone}`}>{children}</span> }
export function PageHeader({ eyebrow, title, description, actions }: { eyebrow: string; title: string; description: string; actions?: ReactNode }) { return <div className="page-header"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{actions && <div className="header-actions">{actions}</div>}</div> }
export function SectionHeading({ title, note, action }: { title: string; note?: string; action?: ReactNode }) { return <div className="section-heading"><div><h2>{title}</h2>{note && <p>{note}</p>}</div>{action}</div> }
export function Empty({ title = 'Your portfolio is empty.', detail = 'Load the demo portfolio or add your first holding.' }: { title?: string; detail?: string }) { return <div className="empty"><Search size={28}/><h3>{title}</h3><p>{detail}</p><Link className="btn primary" to="/portfolio"><Plus size={16}/> Manage holdings</Link></div> }
export function DemoBanner() { return <div className="demo-banner"><Info size={17}/><span>You’re viewing illustrative sample data. Results are not live market data or investment advice.</span><Badge>DEMO WORKSPACE</Badge></div> }
export function Delta({ amount, currency }: { amount: number; currency: Currency }) { return <span className={amount < 0 ? 'negative' : 'positive'}>{amount < 0 ? <ArrowDownRight size={15}/> : <ArrowUpRight size={15}/>} {money(amount, currency)}</span> }
export function RowLink({ to, children }: PropsWithChildren<{ to: string }>) { return <Link className="text-link" to={to}>{children}<ArrowRight size={15}/></Link> }
export function Modal({ title, onClose, children }: PropsWithChildren<{ title: string; onClose: () => void }>) { return <Dialog.Root open onOpenChange={open => { if (!open) onClose() }}><Dialog.Portal><Dialog.Overlay className="modal-backdrop"/><Dialog.Content className="modal"><div className="modal-heading"><Dialog.Title>{title}</Dialog.Title><Dialog.Close className="icon-btn" aria-label="Close dialog"><X size={19}/></Dialog.Close></div><Dialog.Description className="sr-only">Local portfolio action. Review the form or confirm your choice.</Dialog.Description>{children}</Dialog.Content></Dialog.Portal></Dialog.Root> }
