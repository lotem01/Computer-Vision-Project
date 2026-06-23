export type ModelState = 'pending' | 'loading' | 'warming' | 'ready' | 'failed'

export interface ModelMetadata {
  id: string
  label: string
  description: string
  joint_count: number
  joint_names: string[]
  source: string
  state: ModelState
  error?: string | null
}

export interface Readiness {
  apiVersion: 'v1'
  completed: boolean
  readyCount: number
  totalCount: number
  models: ModelMetadata[]
}

export interface Keypoint {
  name: string
  x: number
  y: number
  confidence: number
  visible: boolean
}

export interface PoseResult {
  apiVersion: 'v1'
  frameId?: number | null
  model: ModelMetadata
  keypoints: Keypoint[]
  personBox: { x: number; y: number; width: number; height: number; confidence: number } | null
  sourceSize: [number, number]
  detectedJoints: number
  warnings: string[]
  timing: { inference_ms: number; rendering_ms: number; total_ms: number }
  original: string
  skeleton: string
  avatar: string
}

export interface VideoJob {
  id: string
  state: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled'
  progress: number
  filename: string
  model_id: string
  result_url?: string | null
  avatar_url?: string | null
  skeleton_url?: string | null
  avatar_preview_url?: string | null
  skeleton_preview_url?: string | null
  error?: string | null
}

export interface DecodedVideoResult {
  jobId: string
  filename: string
  source: string
  avatar: string
  skeleton: string
  avatarPreview?: string | null
  skeletonPreview?: string | null
}
