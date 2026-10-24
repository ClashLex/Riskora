import {
  IconChartBar,
  IconChartPie,
  IconDatabaseImport,
  IconFileSearch,
  IconLayoutDashboard,
  IconTargetArrow,
} from '@tabler/icons-react'
import type { Page } from './domain'

export const pages = [
  {
    name: 'Overview',
    short: 'Home',
    title: 'Research overview',
    icon: IconLayoutDashboard,
  },
  {
    name: 'Fund explorer',
    short: 'Funds',
    title: 'Fund disclosures',
    icon: IconChartPie,
  },
  {
    name: 'Predictions',
    short: 'Predict',
    title: 'Candidate rankings',
    icon: IconTargetArrow,
  },
  {
    name: 'Evidence',
    short: 'Signals',
    title: 'Supporting signals',
    icon: IconFileSearch,
  },
  {
    name: 'Evaluation',
    short: 'Results',
    title: 'Model evaluation',
    icon: IconChartBar,
  },
  {
    name: 'Data management',
    short: 'Data',
    title: 'Manage data',
    icon: IconDatabaseImport,
  },
] as const
export const pageHash = (page: Page) => `#${page.toLowerCase().replaceAll(' ', '-')}`
export const pageFromHash = (): Page =>
  pages.find((page) => pageHash(page.name) === window.location.hash)?.name || 'Overview'
