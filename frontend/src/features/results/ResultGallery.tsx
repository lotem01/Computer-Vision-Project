import { Download, Expand, Film, Gauge, Maximize2, ScanLine, TimerReset, X } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useRef, useState } from 'react'
import type { DecodedVideoResult, PoseResult } from '../../types/domain'

const views = [
  { key: 'original', videoKey: 'source', label: 'Source', tag: 'INPUT' },
  { key: 'skeleton', videoKey: 'skeleton', label: 'Pose map', tag: 'VISION' },
  { key: 'avatar', videoKey: 'avatar', label: 'Avatar', tag: 'OUTPUT' },
] as const

type View = (typeof views)[number]
type ViewKey = View['key']
type Props = {
  result: PoseResult | null
  videoResult: DecodedVideoResult | null
  processing: boolean
}
type DisplayMedia = { url: string; kind: 'image' | 'video'; downloadUrl: string }
type VideoRefs = Partial<Record<ViewKey, HTMLVideoElement | null>>

function ResultMedia({
  media,
  view,
  hasVideo,
  registerVideo,
  onSourceSync,
  onExpand,
}: {
  media: DisplayMedia
  view: View
  hasVideo: boolean
  registerVideo: (key: ViewKey, node: HTMLVideoElement | null) => void
  onSourceSync: () => void
  onExpand: () => void
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const isSource = hasVideo && view.videoKey === 'source'
  const isSyncedOutput = hasVideo && view.videoKey !== 'source' && media.kind === 'video'

  const fullscreen = () => containerRef.current?.requestFullscreen?.()

  if (media.kind === 'video') {
    return (
      <div className="controlled-preview" ref={containerRef}>
        <video
          ref={node => registerVideo(view.key, node)}
          src={media.url}
          controls={isSource}
          playsInline
          muted
          preload="metadata"
          onPlay={isSource ? onSourceSync : undefined}
          onPause={isSource ? onSourceSync : undefined}
          onSeeked={isSource ? onSourceSync : undefined}
          onTimeUpdate={isSource ? onSourceSync : undefined}
          onRateChange={isSource ? onSourceSync : undefined}
          onLoadedMetadata={isSyncedOutput ? onSourceSync : undefined}
        />
        {isSyncedOutput && (
          <div className="preview-controls always-visible">
            <button type="button" onClick={fullscreen} aria-label={`Fullscreen ${view.label}`}><Maximize2 size={13} /></button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="controlled-preview" ref={containerRef}>
      <img src={media.url} alt={`${view.label} result`} />
      <button className="expand-button" onClick={onExpand} aria-label={`Expand ${view.label}`}><Expand size={15} /></button>
    </div>
  )
}

export function ResultGallery({ result, videoResult, processing }: Props) {
  const [expanded, setExpanded] = useState<ViewKey | null>(null)
  const videoRefs = useRef<VideoRefs>({})
  const hasVideo = Boolean(videoResult && !result)

  const registerVideo = (key: ViewKey, node: HTMLVideoElement | null) => {
    videoRefs.current[key] = node
  }

  const syncFromSource = () => {
    const source = videoRefs.current.original
    if (!source || !hasVideo) return
    for (const key of ['skeleton', 'avatar'] as const) {
      const target = videoRefs.current[key]
      if (!target || target.readyState < 1) continue
      target.playbackRate = source.playbackRate
      if (Number.isFinite(source.currentTime) && Math.abs(target.currentTime - source.currentTime) > 0.18) {
        target.currentTime = Math.min(source.currentTime, target.duration || source.currentTime)
      }
      if (source.paused) {
        target.pause()
      } else {
        void target.play().catch(() => undefined)
      }
    }
  }

  const mediaFor = (view: View): DisplayMedia | null => {
    if (result) return { url: result[view.key], kind: 'image', downloadUrl: result[view.key] }
    if (videoResult) {
      if (view.videoKey === 'avatar') return { url: videoResult.avatarPreview ?? videoResult.avatar, kind: videoResult.avatarPreviewKind === 'image' ? 'image' : 'video', downloadUrl: videoResult.avatar }
      if (view.videoKey === 'skeleton') return { url: videoResult.skeletonPreview ?? videoResult.skeleton, kind: videoResult.skeletonPreviewKind === 'image' ? 'image' : 'video', downloadUrl: videoResult.skeleton }
      return { url: videoResult.source, kind: 'video', downloadUrl: videoResult.source }
    }
    return null
  }

  const downloadFor = (view: View, media: DisplayMedia) => {
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
        {hasVideo && <div className="result-metrics"><span><Film size={14} /> VIDEO JOB</span><span><ScanLine size={14} /> SYNCED</span><span><Gauge size={14} /> READY</span></div>}
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
                  <ResultMedia media={media} view={view} hasVideo={hasVideo} registerVideo={registerVideo} onSourceSync={syncFromSource} onExpand={() => setExpanded(view.key)} />
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
