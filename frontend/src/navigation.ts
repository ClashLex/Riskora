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
    title: 'Overview',
    icon: IconLayoutDashboard,
    description: 'Disclosure coverage and the next step in your research.',
  },
  {
    name: 'Fund explorer',
    short: 'Funds',
    title: 'Fund explorer',
    icon: IconChartPie,
    description: 'Reported positions, allocations, and changes across disclosures.',
  },
  {
    name: 'Predictions',
    short: 'Predict',
    title: 'Predictions',
    icon: IconTargetArrow,
    description: 'Rank possible new holdings for a later disclosure.',
  },
  {
    name: 'Evidence',
    short: 'Signals',
    title: 'Supporting signals',
    icon: IconFileSearch,
    description: 'Inspect the inputs and sources behind a ranked company.',
  },
  {
    name: 'Evaluation',
    short: 'Results',
    title: 'Evaluation',
    icon: IconChartBar,
    description: 'Compare models and baselines on later periods.',
  },
  {
    name: 'Data management',
    short: 'Data',
    title: 'Data management',
    icon: IconDatabaseImport,
    description: 'Import dated statements, prices, and company disclosures.',
  },
] as const
export const pageHash = (page: Page) => `#${page.toLowerCase().replaceAll(' ', '-')}`
export const pageFromHash = (): Page =>
  pages.find((page) => pageHash(page.name) === window.location.hash)?.name || 'Overview'
