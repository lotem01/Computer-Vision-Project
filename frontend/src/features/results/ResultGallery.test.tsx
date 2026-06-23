import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ResultGallery } from './ResultGallery'

describe('ResultGallery', () => {
  it('renders uploaded video source, pose map, and avatar inside Motion decoded', () => {
    const { container } = render(
      <ResultGallery
        result={null}
        processing={false}
        videoResult={{
          jobId: 'job-1',
          filename: 'motion.mp4',
          source: 'blob:source',
          skeleton: '/api/v1/video-jobs/job-1/result/skeleton',
          avatar: '/api/v1/video-jobs/job-1/result/avatar',
          skeletonPreview: '/api/v1/video-jobs/job-1/preview/skeleton',
          avatarPreview: '/api/v1/video-jobs/job-1/preview/avatar',
        }}
      />,
    )

    expect(screen.getByRole('heading', { name: /motion decoded/i })).toBeInTheDocument()
    expect(screen.getByText('VIDEO JOB')).toBeInTheDocument()
    expect(container.querySelectorAll('.result-frame video')).toHaveLength(1)
    expect(container.querySelectorAll('.result-frame img')).toHaveLength(2)
    expect(container.querySelector('video[src="blob:source"]')).toBeInTheDocument()
    expect(container.querySelector('img[src^="/api/v1/video-jobs/job-1/preview/skeleton"]')).toBeInTheDocument()
    expect(container.querySelector('img[src^="/api/v1/video-jobs/job-1/preview/avatar"]')).toBeInTheDocument()

    const avatarCard = screen.getByText('Avatar').closest('article')!
    expect(within(avatarCard).getByRole('button', { name: 'Pause Avatar' })).toBeInTheDocument()
    expect(within(avatarCard).getByRole('button', { name: 'Restart Avatar' })).toBeInTheDocument()
    expect(within(avatarCard).getByRole('button', { name: 'Fullscreen Avatar' })).toBeInTheDocument()
    expect(within(avatarCard).getByRole('link', { name: /avatar mp4/i })).toHaveAttribute('href', '/api/v1/video-jobs/job-1/result/avatar?download=1')
  })
})
