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
    title: 'Research overview',
    description: 'A quick read of disclosure coverage and what to do next.',
    icon: IconLayoutDashboard,
  },
  {
    name: 'Fund explorer',
    title: 'Fund disclosures',
    description: 'Compare report dates and inspect holdings in each statement.',
    icon: IconChartPie,
  },
  {
    name: 'Predictions',
    title: 'Candidate rankings',
    description:
      'Choose a fund and period to rank possible new positions. Scores are relative, not probabilities.',
    icon: IconTargetArrow,
  },
  {
    name: 'Evidence',
    title: 'Supporting signals',
    description: 'Trace score inputs, contributions, and sources available by the cutoff.',
    icon: IconFileSearch,
  },
  {
    name: 'Evaluation',
    title: 'Model evaluation',
    description: 'Check training readiness and later period results before using a ranking.',
    icon: IconChartBar,
  },
  {
    name: 'Data management',
    title: 'Manage data',
    description: 'Import dated disclosures, review identifiers, and keep samples separate.',
    icon: IconDatabaseImport,
  },
] as const
export const pageHash = (page: Page) => `#${page.toLowerCase().replaceAll(' ', '-')}`
export const pageFromHash = (): Page =>
  pages.find((page) => pageHash(page.name) === window.location.hash)?.name || 'Overview'
