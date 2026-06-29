import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { UploadPanel } from './UploadPanel'

const apiMock = vi.hoisted(() => ({
  submitVideo: vi.fn(),
  videoJob: vi.fn(),
  inferImage: vi.fn(),
}))

vi.mock('../../api/client', () => ({ api: apiMock }))

describe('UploadPanel', () => {
  beforeEach(() => {
    apiMock.submitVideo.mockReset()
    apiMock.videoJob.mockReset()
    apiMock.inferImage.mockReset()
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:preview-video'),
      revokeObjectURL: vi.fn(),
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('sends completed video results to Motion decoded and keeps downloads in the upload HUD', async () => {
    apiMock.submitVideo.mockResolvedValue({
      id: 'job-1',
      state: 'processing',
      progress: 25,
      filename: 'motion.mp4',
      model_id: 'yolov8n_pose',
      result_url: null,
    })
    apiMock.videoJob.mockResolvedValue({
      id: 'job-1',
      state: 'completed',
      progress: 100,
      filename: 'motion.mp4',
      model_id: 'yolov8n_pose',
      result_url: '/api/v1/video-jobs/job-1/result/avatar',
      avatar_url: '/api/v1/video-jobs/job-1/result/avatar',
      skeleton_url: '/api/v1/video-jobs/job-1/result/skeleton',
      avatar_preview_url: '/api/v1/video-jobs/job-1/preview/avatar',
      skeleton_preview_url: '/api/v1/video-jobs/job-1/preview/skeleton',
      avatar_preview_kind: 'image',
      skeleton_preview_kind: 'image',
    })
    const onProcessing = vi.fn()
    const onVideoResult = vi.fn()
    const { container } = render(<UploadPanel modelId="yolov8n_pose" offlineFps={9} onResult={vi.fn()} onVideoResult={onVideoResult} onProcessing={onProcessing} onError={vi.fn()} />)

    const input = container.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['video'], 'motion.mp4', { type: 'video/mp4' })
    fireEvent.change(input, { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: /render avatar video/i }))

    await waitFor(() => expect(apiMock.submitVideo).toHaveBeenCalledWith(file, 'yolov8n_pose', 9))

    expect(await screen.findByText('Video ready in Motion decoded')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /preview/i })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /avatar mp4/i })).toHaveAttribute('href', '/api/v1/video-jobs/job-1/result/avatar?download=1')
    expect(screen.getByRole('link', { name: /pose map mp4/i })).toHaveAttribute('href', '/api/v1/video-jobs/job-1/result/skeleton?download=1')
    expect(container.querySelector('video')).toHaveAttribute('src', 'blob:preview-video')
    expect(onVideoResult).toHaveBeenLastCalledWith({
      jobId: 'job-1',
      filename: 'motion.mp4',
      source: 'blob:preview-video',
      avatar: '/api/v1/video-jobs/job-1/result/avatar',
      skeleton: '/api/v1/video-jobs/job-1/result/skeleton',
      avatarPreview: '/api/v1/video-jobs/job-1/preview/avatar',
      skeletonPreview: '/api/v1/video-jobs/job-1/preview/skeleton',
      avatarPreviewKind: 'image',
      skeletonPreviewKind: 'image',
    })
    expect(onProcessing).toHaveBeenCalledWith(false)
  })

})
