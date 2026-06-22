import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ModelRail } from './ModelRail'

const models = [{
  id: 'ready', label: 'Ready model', description: 'Available', joint_count: 17,
  joint_names: [], source: 'Test', state: 'ready' as const,
}, {
  id: 'failed', label: 'Failed model', description: 'Unavailable', joint_count: 13,
  joint_names: [], source: 'Test', state: 'failed' as const, error: 'bad weights',
}]

describe('ModelRail', () => {
  it('selects only ready models', () => {
    const select = vi.fn()
    render(<ModelRail models={models} selected="ready" onSelect={select} />)
    fireEvent.click(screen.getByText('Ready model'))
    expect(select).toHaveBeenCalledWith('ready')
    expect(screen.getByText('Failed model').closest('button')).toBeDisabled()
  })
})

