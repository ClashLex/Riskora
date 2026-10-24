import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './stage.css'
import './page-design.css'
import Stage from './Stage.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Stage />
  </StrictMode>,
)
