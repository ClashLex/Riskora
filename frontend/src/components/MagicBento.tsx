import type { CSSProperties, PointerEvent, ReactNode } from 'react'
import './MagicBento.css'

export interface MagicBentoItem {
  id: string
  label: string
  value: ReactNode
  colSpan?: number
}

function positionSpotlight(event: PointerEvent<HTMLDivElement>) {
  if (event.pointerType !== 'mouse' && event.pointerType !== 'pen') return

  const card = event.currentTarget
  const bounds = card.getBoundingClientRect()
  card.style.setProperty('--mb-x', `${event.clientX - bounds.left}px`)
  card.style.setProperty('--mb-y', `${event.clientY - bounds.top}px`)
}

export function MagicBento({
  items,
  label,
  columns = 3,
}: {
  items: MagicBentoItem[]
  label: string
  columns?: number
}) {
  return (
    <dl
      className="magic-bento"
      aria-label={label}
      style={{ '--mb-columns': Math.max(1, columns) } as CSSProperties}
    >
      {items.map((item) => (
        <div
          className="magic-bento__cell"
          key={item.id}
          onPointerMove={positionSpotlight}
          style={
            { '--mb-span': Math.min(columns, Math.max(1, item.colSpan || 1)) } as CSSProperties
          }
        >
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}
