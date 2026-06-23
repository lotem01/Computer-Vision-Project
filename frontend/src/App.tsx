import { AnimatePresence, motion } from 'motion/react'
import { Camera, ChevronDown, CircleHelp, CloudOff, Film, ImageUp, Menu, Settings2, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { api } from './api/client'
import { Brand } from './components/Brand'
import { CameraPanel } from './features/camera/CameraPanel'
import { ModelRail } from './features/models/ModelRail'
import { ReadinessScreen } from './features/readiness/ReadinessScreen'
import { ResultGallery } from './features/results/ResultGallery'
import { UploadPanel } from './features/upload/UploadPanel'
import { useReadiness } from './hooks/useReadiness'
import type { DecodedVideoResult, PoseResult, VideoJob } from './types/domain'

function App() {
  const { data: readiness, connected } = useReadiness()
  const [entered, setEntered] = useState(false)
  const [selectedModel, setSelectedModel] = useState('')
  const [mode, setMode] = useState<'camera' | 'upload'>('camera')
  const [result, setResult] = useState<PoseResult | null>(null)
  const [videoResult, setVideoResult] = useState<DecodedVideoResult | null>(null)
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [videoJob, setVideoJob] = useState<VideoJob | null>(null)
  const [videoJobSource, setVideoJobSource] = useState<string | null>(null)

  const readyModels = useMemo(() => readiness?.models.filter(model => model.state === 'ready') ?? [], [readiness])
  useEffect(() => { if (!selectedModel && readyModels[0]) setSelectedModel(readyModels[0].id) }, [readyModels, selectedModel])
  useEffect(() => {
    if (!videoJob || !['queued', 'processing'].includes(videoJob.state)) return
    const timer = setTimeout(async () => {
      try {
        const next = await api.videoJob(videoJob.id)
        setVideoJob(next)
        if (next.state === 'completed' && videoJobSource && (next.avatar_url || next.result_url) && next.skeleton_url) {
          setResult(null)
          setVideoResult({
            jobId: next.id,
            filename: next.filename,
            source: videoJobSource,
            avatar: next.avatar_url ?? next.result_url!,
            skeleton: next.skeleton_url,
            avatarPreview: next.avatar_preview_url,
            skeletonPreview: next.skeleton_preview_url,
          })
        }
      } catch (err) { setError((err as Error).message) }
    }, 700)
    return () => clearTimeout(timer)
  }, [videoJob, videoJobSource])

  const acceptResult = (next: PoseResult) => { setVideoResult(null); setResult(current => !current || (next.frameId ?? 0) >= (current.frameId ?? 0) ? next : current); setProcessing(false) }
  const acceptVideoResult = (next: DecodedVideoResult | null) => { setResult(null); setVideoResult(next); setProcessing(false) }
  const acceptVideo = async (file: File) => {
    setProcessing(true)
    setResult(null)
    setVideoResult(null)
    setVideoJobSource(URL.createObjectURL(file))
    try { setVideoJob(await api.submitVideo(file, selectedModel)) } catch (err) { setError((err as Error).message) } finally { setProcessing(false) }
  }

  return (
    <AnimatePresence mode="wait">
      {!entered ? <ReadinessScreen key="readiness" data={readiness} connected={connected} onEnter={() => readiness?.completed && setEntered(true)} /> :
        <motion.div className="app-shell" key="studio" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div className="ambient ambient-one" /><div className="ambient ambient-two" />
          <header className="topbar"><Brand /><nav><a href="#studio" className="active">Studio</a><a href="#models">Models</a><a href="#about">About</a></nav><div className="top-actions"><span className="local-chip"><i /> LOCAL ENGINE</span><button aria-label="Help"><CircleHelp size={18} /></button><button aria-label="Settings"><Settings2 size={18} /></button><button className="menu-button" aria-label="Menu"><Menu size={18} /></button></div></header>
          <main>
            <section className="hero"><div><span className="eyebrow"><span className="live-dot" /> HUMAN MOTION · MACHINE INTELLIGENCE</span><h1>Turn movement into<br /><em>something extraordinary.</em></h1><p>Four pose engines. One expressive canvas. Capture a human moment and watch intelligence reconstruct it in real time.</p></div><aside><span>SESSION</span><strong>01</strong><small>ALL SYSTEMS<br />OPERATIONAL</small></aside></section>
            <ModelRail models={readiness?.models ?? []} selected={selectedModel} onSelect={setSelectedModel} />
            <section className="capture-section" id="studio">
              <div className="section-heading"><div><span className="step-number">02</span><div><h2>Feed the signal</h2><p>Move live, capture a frame, or bring your own footage.</p></div></div><div className="mode-tabs"><button className={mode === 'camera' ? 'active' : ''} onClick={() => setMode('camera')}><Camera size={15} /> Live camera</button><button className={mode === 'upload' ? 'active' : ''} onClick={() => setMode('upload')}><ImageUp size={15} /> Upload media</button></div></div>
              <AnimatePresence mode="wait">{mode === 'camera' ? <motion.div key="camera" initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 8 }}><CameraPanel modelId={selectedModel} onResult={acceptResult} onProcessing={setProcessing} onError={setError} onVideo={acceptVideo} /></motion.div> : <motion.div key="upload" initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}><UploadPanel modelId={selectedModel} onResult={acceptResult} onVideoResult={acceptVideoResult} onProcessing={value => { if (value) { setResult(null); setVideoResult(null) }; setProcessing(value) }} onError={setError} /></motion.div>}</AnimatePresence>
            </section>
            <ResultGallery result={result} videoResult={videoResult} processing={processing} />
          </main>
          <footer className="site-footer"><Brand /><span>Human Pose Estimation · Project 7</span><span>Idan · Lotem · Shahaf</span></footer>
          <AnimatePresence>{error && <motion.div className="toast error-toast" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}><CloudOff size={18} /><div><strong>Signal interrupted</strong><span>{error}</span></div><button onClick={() => setError(null)}><X size={15} /></button></motion.div>}</AnimatePresence>
          <AnimatePresence>{videoJob && <motion.div className={`toast job-toast ${videoJob.state}`} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}><Film size={18} /><div><strong>{videoJob.state === 'completed' ? 'Avatar sequence ready' : 'Rendering motion'}</strong><span>{videoJob.state === 'failed' ? videoJob.error : `${Math.round(videoJob.progress)}% · ${videoJob.filename}`}</span></div><button onClick={() => setVideoJob(null)}><ChevronDown size={16} /></button></motion.div>}</AnimatePresence>
        </motion.div>}
    </AnimatePresence>
  )
}

export default App
