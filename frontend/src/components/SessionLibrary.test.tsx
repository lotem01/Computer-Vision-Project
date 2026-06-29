import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SessionLibrary } from './SessionLibrary'

describe('SessionLibrary', () => {
  it('shows an empty hint before videos are rendered', () => {
    render(<SessionLibrary items={[]} onSelect={vi.fn()} />)

    expect(screen.getByText('Rendered this session')).toBeInTheDocument()
    expect(screen.getByText(/render or record a video/i)).toBeInTheDocument()
  })

  it('exposes rendered session media for quick reuse', () => {
    const onSelect = vi.fn()
    render(<SessionLibrary items={[{
      jobId: 'cached-1',
      filename: 'cached.mp4',
      source: 'blob:cached',
      avatar: '/avatar.mp4',
      skeleton: '/skeleton.mp4',
      avatarPreview: '/avatar.webm',
      skeletonPreview: '/skeleton.webm',
      avatarPreviewKind: 'image',
      skeletonPreviewKind: 'image',
    }]} onSelect={onSelect} />)

    fireEvent.click(screen.getByRole('button', { name: /cached.mp4/i }))

    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ jobId: 'cached-1' }))
  })
})
