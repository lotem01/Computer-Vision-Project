import { Download, Expand, Film, Gauge, Maximize2, Pause, Play, RotateCcw, ScanLine, TimerReset, X } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useRef, useState } from 'react'
import type { DecodedVideoResult, PoseResult } from '../../types/domain'

const views = [
  { key: 'original', videoKey: 'source', label: 'Source', tag: 'INPUT' },
  { key: 'skeleton', videoKey: 'skeleton', label: 'Pose map', tag: 'VISION' },
  { key: 'avatar', videoKey: 'avatar', label: 'Avatar', tag: 'OUTPUT' },
] as const

type ViewKey = (typeof views)[number]['key']
type Props = {
  result: PoseResult | null
  videoResult: DecodedVideoResult | null
  processing: boolean
}
type DisplayMedia = { url: string; kind: 'image' | 'video'; downloadUrl: string }

function ControlledPreview({ media, label, onExpand }: { media: DisplayMedia; label: string; onExpand: () => void }) {
  const frameRef = useRef<HTMLDivElement>(null)
  const imageRef = useRef<HTMLImageElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [paused, setPaused] = useState(false)
  const [version, setVersion] = useState(0)
  const isAnimatedPreview = media.kind === 'image' && media.url.includes('/preview/')
  const previewUrl = isAnimatedPreview ? `${media.url}${media.url.includes('?') ? '&' : '?'}v=${version}` : media.url

  const pausePreview = () => {
    const image = imageRef.current
    const canvas = canvasRef.current
    if (!image || !canvas) return
    canvas.width = image.naturalWidth || image.clientWidth
    canvas.height = image.naturalHeight || image.clientHeight
    canvas.getContext('2d')?.drawImage(image, 0, 0, canvas.width, canvas.height)
    setPaused(true)
  }

  const playPreview = () => setPaused(false)
  const restartPreview = () => { setPaused(false); setVersion(current => current + 1) }
  const fullscreen = () => frameRef.current?.requestFullscreen?.()

  if (media.kind === 'video') {
    return (
      <div className="controlled-preview" ref={frameRef}>
        <video src={media.url} controls playsInline muted preload="metadata" />
        <button className="expand-button" onClick={onExpand} aria-label={`Expand ${label}`}><Expand size={15} /></button>
      </div>
    )
  }

  return (
    <div className="controlled-preview" ref={frameRef}>
      <img ref={imageRef} src={previewUrl} alt={`${label} result`} className={paused ? 'is-paused' : ''} />
      <canvas ref={canvasRef} className={`preview-freeze ${paused ? 'visible' : ''}`} aria-hidden="true" />
      {isAnimatedPreview && (
        <div className="preview-controls" aria-label={`${label} playback controls`}>
          <button type="button" onClick={paused ? playPreview : pausePreview} aria-label={`${paused ? 'Play' : 'Pause'} ${label}`}>
            {paused ? <Play size={13} /> : <Pause size={13} />}
          </button>
          <button type="button" onClick={restartPreview} aria-label={`Restart ${label}`}><RotateCcw size={13} /></button>
          <button type="button" onClick={fullscreen} aria-label={`Fullscreen ${label}`}><Maximize2 size={13} /></button>
          <button type="button" onClick={onExpand} aria-label={`Expand ${label}`}><Expand size={13} /></button>
        </div>
      )}
      {!isAnimatedPreview && <button className="expand-button" onClick={onExpand} aria-label={`Expand ${label}`}><Expand size={15} /></button>}
    </div>
  )
}

export function ResultGallery({ result, videoResult, processing }: Props) {
  const [expanded, setExpanded] = useState<ViewKey | null>(null)
  const hasVideo = Boolean(videoResult && !result)

  const mediaFor = (view: (typeof views)[number]): DisplayMedia | null => {
    if (result) return { url: result[view.key], kind: 'image', downloadUrl: result[view.key] }
    if (videoResult) {
      if (view.videoKey === 'avatar') {
        return { url: videoResult.avatarPreview ?? videoResult.avatar, kind: videoResult.avatarPreview ? 'image' : 'video', downloadUrl: videoResult.avatar }
      }
      if (view.videoKey === 'skeleton') {
        return { url: videoResult.skeletonPreview ?? videoResult.skeleton, kind: videoResult.skeletonPreview ? 'image' : 'video', downloadUrl: videoResult.skeleton }
      }
      return { url: videoResult.source, kind: 'video', downloadUrl: videoResult.source }
    }
    return null
  }

  const downloadFor = (view: (typeof views)[number], media: DisplayMedia) => {
    if (!hasVideo) return { href: media.downloadUrl, label: 'Export', filename: `poselab-${view.key}.jpg` }
    if (view.videoKey === 'source') return { href: media.downloadUrl, label: 'Source', filename: videoResult?.filename ?? 'source-video.mp4' }
    return { href: `${media.downloadUrl}?download=1`, label: view.videoKey === 'avatar' ? 'Avatar MP4' : 'Pose map MP4', filename: `poselab-${view.videoKey}.mp4` }
  }

  const expandedView = views.find(view => view.key === expanded)
  const expandedMedia = expandedView ? mediaFor(expandedView) : null

  return (
    <section className="result-section" aria-labelledby="result-heading">
      <div className="section-heading">
        <div><span className="step-number">03</span><div><h2 id="result-heading">Motion decoded</h2><p>Source, structure, and expression — synchronized.</p></div></div>
        {result && <div className="result-metrics"><span><TimerReset size={14} /> {Math.round(result.timing.total_ms)} ms</span><span><ScanLine size={14} /> {result.detectedJoints}/{result.model.joint_count}</span><span><Gauge size={14} /> {Math.round((result.personBox?.confidence ?? 0) * 100)}%</span></div>}
        {hasVideo && <div className="result-metrics"><span><Film size={14} /> VIDEO JOB</span><span><ScanLine size={14} /> POSE MAP</span><span><Gauge size={14} /> READY</span></div>}
      </div>
      <div className="result-grid">
        {views.map((view, index) => {
          const media = mediaFor(view)
          const download = media ? downloadFor(view, media) : null
          return (
            <article className={`result-card ${view.key === 'avatar' ? 'featured' : ''}`} key={view.key}>
              <header><span><i>0{index + 1}</i>{view.label}</span><small>{view.tag}</small></header>
              <div className="result-frame">
                {media ? (
                  <ControlledPreview media={media} label={view.label} onExpand={() => setExpanded(view.key)} />
                ) : (
                  <div className={`empty-visual empty-${index}`}><span className="empty-scan" /><div>{processing ? 'PROCESSING SIGNAL' : index === 0 ? 'AWAITING INPUT' : 'NO SIGNAL'}</div></div>
                )}
                {processing && <div className="processing-shimmer" />}
              </div>
              <footer>
                {download ? <><span className="signal"><i /> {hasVideo ? 'VIDEO READY' : 'SIGNAL LOCKED'}</span><a href={download.href} download={download.filename}><Download size={13} /> {download.label}</a></> : <span>—</span>}
              </footer>
            </article>
          )
        })}
      </div>
      <AnimatePresence>{expanded && expandedMedia && <motion.div className="lightbox" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setExpanded(null)}><button><X /></button>{expandedMedia.kind === 'video' ? <motion.video initial={{ scale: .94 }} animate={{ scale: 1 }} src={expandedMedia.url} controls playsInline autoPlay muted /> : <motion.img initial={{ scale: .94 }} animate={{ scale: 1 }} src={expandedMedia.url} alt="Expanded result" />}</motion.div>}</AnimatePresence>
    </section>
  )
}
