import { Download, Film, Image as ImageIcon, Sparkles, UploadCloud, X } from 'lucide-react'
import { ChangeEvent, DragEvent, useEffect, useRef, useState } from 'react'
import { motion } from 'motion/react'
import { api } from '../../api/client'
import type { DecodedVideoResult, PoseResult, VideoJob } from '../../types/domain'

interface Props {
  modelId: string
  onResult: (result: PoseResult) => void
  onVideoResult: (result: DecodedVideoResult | null) => void
  onProcessing: (value: boolean) => void
  onError: (message: string) => void
}

export function UploadPanel({ modelId, onResult, onVideoResult, onProcessing, onError }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const [job, setJob] = useState<VideoJob | null>(null)

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])
  useEffect(() => {
    if (!job || !['queued', 'processing'].includes(job.state)) return
    const timer = window.setTimeout(async () => {
      try {
        const next = await api.videoJob(job.id)
        setJob(next)
        if (next.state === 'completed' || next.state === 'failed') onProcessing(false)
        if (next.state === 'completed' && preview && (next.avatar_url || next.result_url) && next.skeleton_url) {
          onVideoResult({
            jobId: next.id,
            filename: next.filename,
            source: preview,
            avatar: next.avatar_url ?? next.result_url!,
            skeleton: next.skeleton_url,
            avatarPreview: next.avatar_preview_url,
            skeletonPreview: next.skeleton_preview_url,
          })
        }
        if (next.error) onError(next.error)
      } catch (error) {
        onError((error as Error).message)
        onProcessing(false)
      }
    }, 700)
    return () => clearTimeout(timer)
  }, [job, onError, onProcessing, onVideoResult, preview])

  const accept = (next: File) => {
    if (!next.type.startsWith('image/') && !next.type.startsWith('video/')) return onError('Choose an image or video file.')
    onVideoResult(null)
    if (preview) URL.revokeObjectURL(preview)
    setFile(next)
    setPreview(URL.createObjectURL(next))
    setJob(null)
  }

  const analyze = async () => {
    if (!file) return
    onProcessing(true)
    try {
      if (file.type.startsWith('video/')) {
        const created = await api.submitVideo(file, modelId)
        setJob(created)
      } else {
        onResult(await api.inferImage(file, modelId))
        onProcessing(false)
      }
    } catch (error) {
      onError((error as Error).message)
      onProcessing(false)
    }
  }

  const useSample = async () => {
    const canvas = document.createElement('canvas')
    canvas.width = 720
    canvas.height = 900
    const ctx = canvas.getContext('2d')!
    const gradient = ctx.createLinearGradient(0, 0, 720, 900)
    gradient.addColorStop(0, '#d7d2cb')
    gradient.addColorStop(1, '#9e9892')
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, 720, 900)
    ctx.fillStyle = '#1a1722'
    ctx.beginPath()
    ctx.arc(360, 145, 72, 0, Math.PI * 2)
    ctx.fill()
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.strokeStyle = '#241f2d'
    ctx.lineWidth = 78
    ctx.beginPath()
    ctx.moveTo(360, 240)
    ctx.lineTo(355, 520)
    ctx.moveTo(355, 310)
    ctx.lineTo(190, 430)
    ctx.lineTo(115, 620)
    ctx.moveTo(355, 310)
    ctx.lineTo(530, 385)
    ctx.lineTo(620, 245)
    ctx.moveTo(355, 515)
    ctx.lineTo(245, 665)
    ctx.lineTo(195, 855)
    ctx.moveTo(355, 515)
    ctx.lineTo(475, 675)
    ctx.lineTo(555, 855)
    ctx.stroke()
    ctx.fillStyle = '#cc3f85'
    ctx.beginPath()
    ctx.roundRect(300, 225, 115, 320, 50)
    ctx.fill()
    const blob = await new Promise<Blob>(resolve => canvas.toBlob(value => resolve(value!), 'image/jpeg', .92))
    accept(new File([blob], 'presentation-sample.jpg', { type: 'image/jpeg' }))
  }

  const drop = (event: DragEvent) => {
    event.preventDefault()
    setDragging(false)
    const next = event.dataTransfer.files[0]
    if (next) accept(next)
  }
  const change = (event: ChangeEvent<HTMLInputElement>) => {
    const next = event.target.files?.[0]
    if (next) accept(next)
  }

  const isVideo = file?.type.startsWith('video/') ?? false

  return (
    <div className="input-panel upload-panel">
      {!file ? (
        <motion.div className={`drop-zone ${dragging ? 'dragging' : ''}`} onDragOver={event => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={drop} onClick={() => inputRef.current?.click()} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div className="drop-icon"><UploadCloud size={25} /></div>
          <span className="drop-kicker">DROP YOUR MOTION</span>
          <h3>Upload an image or video</h3>
          <p>Drag it here, or click to browse your files.</p>
          <div className="format-row"><span>JPG</span><span>PNG</span><span>WEBP</span><span>MP4</span><span>MOV</span></div>
          <input ref={inputRef} type="file" accept="image/*,video/*" hidden onChange={change} />
          <button className="sample-button" onClick={event => { event.stopPropagation(); useSample() }}><Sparkles size={14} /> Try presentation sample</button>
        </motion.div>
      ) : (
        <div className="media-preview">
          {isVideo ? <video key={preview} src={preview!} controls playsInline /> : <img src={preview!} alt="Selected input" />}
          <div className="media-overlay">
            <span>{isVideo ? <Film /> : <ImageIcon />}{file.name}</span>
            <button onClick={() => { onVideoResult(null); setFile(null); setPreview(null); setJob(null) }}><X size={16} /></button>
          </div>
          {job && (
            <div className="job-progress">
              <div><span>{job.state === 'completed' ? 'Video ready in Motion decoded' : 'Rendering avatar sequence'}</span><strong>{Math.round(job.progress)}%</strong></div>
              <div className="progress-track"><motion.div animate={{ width: `${job.progress}%` }} /></div>
              {job.state === 'completed' && (
                <div className="video-downloads">
                  <a href={`${job.avatar_url ?? job.result_url}?download=1`} download><Download size={13} /> Avatar MP4</a>
                  {job.skeleton_url && <a href={`${job.skeleton_url}?download=1`} download><Download size={13} /> Pose map MP4</a>}
                </div>
              )}
            </div>
          )}
        </div>
      )}
      <button className="analyze-button" disabled={!file || !!job && ['queued', 'processing'].includes(job.state)} onClick={analyze}><span>{isVideo ? 'Render avatar video' : 'Decode pose'}</span><i>↗</i></button>
    </div>
  )
}
