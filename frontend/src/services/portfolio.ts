import { demoHoldings } from '../data'
import { z } from 'zod'
import { currencies } from '../data'
import type { Holding } from '../types'

const key = 'risvanta-demo-holdings-v1'
const holdingSchema = z.object({ id: z.string(), name: z.string(), ticker: z.string().optional(), assetClass: z.enum(['stock','etf','mutual_fund','bond','cash','other']), marketValue: z.number().finite().positive(), currency: z.enum(currencies), country: z.string().optional(), sector: z.string().optional(), quantity: z.number().finite().nonnegative().optional(), sourceLabel: z.string(), asOfDate: z.string(), isDemo: z.boolean() })
export function getPortfolio(): Holding[] { try { const saved = localStorage.getItem(key); return saved ? z.array(holdingSchema).parse(JSON.parse(saved)) : demoHoldings.map(h => ({ ...h })) } catch { return demoHoldings.map(h => ({ ...h })) } }
export function savePortfolio(holdings: Holding[]) { localStorage.setItem(key, JSON.stringify(holdings)) }
export function resetPortfolio() { savePortfolio(demoHoldings.map(h => ({ ...h }))); return demoHoldings.map(h => ({ ...h })) }
