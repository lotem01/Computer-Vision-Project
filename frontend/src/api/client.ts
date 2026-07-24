import type { ExerciseCompareResult, ExerciseInstructor, ExerciseSummary, PoseResult, Readiness, VideoJob } from '../types/domain'

const API = '/api/v1'

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = await response.json()
      message = body.detail || message
    } catch { /* keep the status message */ }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export const api = {
  async readiness(signal?: AbortSignal) {
    return json<Readiness>(await fetch(`${API}/readiness`, { signal }))
  },

  async inferImage(file: File | Blob, modelId: string, diffusion = false) {
    const form = new FormData()
    form.append('modelId', modelId)
    form.append('image', file, file instanceof File ? file.name : 'capture.jpg')
    return json<PoseResult>(await fetch(`${API}/infer/${diffusion ? 'diffusion' : 'image'}`, { method: 'POST', body: form }))
  },

  async submitVideo(file: File, modelId: string, renderFps?: number) {
    const form = new FormData()
    form.append('modelId', modelId)
    if (renderFps) form.append('renderFps', String(renderFps))
    form.append('video', file)
    return json<VideoJob>(await fetch(`${API}/video-jobs`, { method: 'POST', body: form }))
  },

  async videoJob(id: string) {
    return json<VideoJob>(await fetch(`${API}/video-jobs/${id}`))
  },

  async cancelVideo(id: string) {
    return json<VideoJob>(await fetch(`${API}/video-jobs/${id}`, { method: 'DELETE' }))
  },

  liveSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    return new WebSocket(`${protocol}//${location.host}${API}/live`)
  },

  async exerciseInstructors() {
    return json<{ apiVersion: 'v1'; items: ExerciseInstructor[] }>(await fetch(`${API}/exercise/instructors`))
  },

  async submitExerciseInstructor(file: File, modelId: string, renderFps?: number) {
    const form = new FormData()
    form.append('modelId', modelId)
    if (renderFps) form.append('renderFps', String(renderFps))
    form.append('video', file)
    return json<ExerciseInstructor>(await fetch(`${API}/exercise/instructors`, { method: 'POST', body: form }))
  },

  async exerciseInstructor(id: string) {
    return json<ExerciseInstructor>(await fetch(`${API}/exercise/instructors/${id}`))
  },

  async compareExerciseFrame(instructorId: string, frameIndex: number, modelId: string, image: Blob) {
    const form = new FormData()
    form.append('instructorId', instructorId)
    form.append('frameIndex', String(frameIndex))
    form.append('modelId', modelId)
    form.append('image', image, 'exercise-frame.jpg')
    return json<ExerciseCompareResult>(await fetch(`${API}/exercise/compare`, { method: 'POST', body: form }))
  },

  async exerciseSummary(samples: ExerciseCompareResult[]) {
    return json<ExerciseSummary>(await fetch(`${API}/exercise/summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(samples),
    }))
  },
}
