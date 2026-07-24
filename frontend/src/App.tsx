import { AnimatePresence, motion } from 'motion/react'
import { Camera, ChevronDown, CircleHelp, CloudOff, Dumbbell, Film, ImageUp, Menu, Settings2, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { api } from './api/client'
import { Brand } from './components/Brand'
import { SessionLibrary } from './components/SessionLibrary'
import { CameraPanel } from './features/camera/CameraPanel'
import { ExerciseMode } from './features/exercise/ExerciseMode'
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
  const [windowMode, setWindowMode] = useState<'studio' | 'exercise'>('studio')
  const [result, setResult] = useState<PoseResult | null>(null)
  const [videoResult, setVideoResult] = useState<DecodedVideoResult | null>(null)
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [videoJob, setVideoJob] = useState<VideoJob | null>(null)
  const [videoJobSource, setVideoJobSource] = useState<string | null>(null)
  const [liveFps, setLiveFps] = useState(4)
  const [offlineFps, setOfflineFps] = useState(12)
  const [sessionVideos, setSessionVideos] = useState<DecodedVideoResult[]>([])

  const readyModels = useMemo(() => readiness?.models.filter(model => model.state === 'ready') ?? [], [readiness])
  useEffect(() => { if (!selectedModel && readyModels[0]) setSelectedModel(readyModels[0].id) }, [readyModels, selectedModel])
  useEffect(() => {
    if (!videoJob || !['queued', 'processing'].includes(videoJob.state)) return
    const timer = setTimeout(async () => {
      try {
        const next = await api.videoJob(videoJob.id)
        setVideoJob(next)
        if (next.state === 'completed' && videoJobSource && (next.avatar_url || next.result_url) && next.skeleton_url) {
          const completedVideo: DecodedVideoResult = {
            jobId: next.id,
            filename: next.filename,
            source: videoJobSource,
            avatar: next.avatar_url ?? next.result_url!,
            skeleton: next.skeleton_url,
            avatarPreview: next.avatar_preview_url,
            skeletonPreview: next.skeleton_preview_url,
            avatarPreviewKind: next.avatar_preview_kind,
            skeletonPreviewKind: next.skeleton_preview_kind,
          }
          setResult(null)
          setVideoResult(completedVideo)
          setSessionVideos(current => current.some(item => item.jobId === next.id) ? current : [completedVideo, ...current].slice(0, 8))
        }
      } catch (err) { setError((err as Error).message) }
    }, 700)
    return () => clearTimeout(timer)
  }, [videoJob, videoJobSource])

  const acceptResult = (next: PoseResult) => { setVideoResult(null); setResult(current => !current || (next.frameId ?? 0) >= (current.frameId ?? 0) ? next : current); setProcessing(false) }
  const acceptVideoResult = (next: DecodedVideoResult | null) => {
    setResult(null)
    setVideoResult(next)
    if (next) setSessionVideos(current => current.some(item => item.jobId === next.jobId) ? current : [next, ...current].slice(0, 8))
    setProcessing(false)
  }
  const acceptVideo = async (file: File) => {
    setProcessing(true)
    setResult(null)
    setVideoResult(null)
    setVideoJobSource(URL.createObjectURL(file))
    try { setVideoJob(await api.submitVideo(file, selectedModel, offlineFps)) } catch (err) { setError((err as Error).message) } finally { setProcessing(false) }
  }

  return (
    <AnimatePresence mode="wait">
      {!entered ? <ReadinessScreen key="readiness" data={readiness} connected={connected} onEnter={() => readiness?.completed && setEntered(true)} /> :
        <motion.div className="app-shell" key="studio" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div className="ambient ambient-one" /><div className="ambient ambient-two" />
          <header className="topbar"><Brand /><nav><button className={windowMode === 'studio' ? 'active' : ''} onClick={() => setWindowMode('studio')}>Pose Studio</button><button className={windowMode === 'exercise' ? 'active' : ''} onClick={() => setWindowMode('exercise')}>Exercise Mode</button><a href="#models">Models</a></nav><div className="top-actions"><span className="local-chip"><i /> LOCAL ENGINE</span><button aria-label="Help"><CircleHelp size={18} /></button><button aria-label="Settings"><Settings2 size={18} /></button><button className="menu-button" aria-label="Menu"><Menu size={18} /></button></div></header>
          <main>
            <section className="hero"><div><span className="eyebrow"><span className="live-dot" /> HUMAN MOTION · MACHINE INTELLIGENCE</span><h1>Turn movement into<br /><em>something extraordinary.</em></h1><p>Four pose engines. One expressive canvas. Capture a human moment and watch intelligence reconstruct it in real time.</p></div><aside><span>SESSION</span><strong>01</strong><small>ALL SYSTEMS<br />OPERATIONAL</small></aside></section>
            <ModelRail models={readiness?.models ?? []} selected={selectedModel} onSelect={setSelectedModel} />
            <div className="window-switch" aria-label="Application mode">
              <button className={windowMode === 'studio' ? 'active' : ''} onClick={() => setWindowMode('studio')}><Camera size={16} /> Pose Studio</button>
              <button className={windowMode === 'exercise' ? 'active' : ''} onClick={() => setWindowMode('exercise')}><Dumbbell size={16} /> Exercise Mode</button>
            </div>
            {windowMode === 'studio' ? <>
            <section className="capture-section" id="studio">
              <div className="section-heading"><div><span className="step-number">02</span><div><h2>Feed the signal</h2><p>Move live, capture a frame, or bring your own footage.</p></div></div><div className="mode-tabs"><button className={mode === 'camera' ? 'active' : ''} onClick={() => setMode('camera')}><Camera size={15} /> Live camera</button><button className={mode === 'upload' ? 'active' : ''} onClick={() => setMode('upload')}><ImageUp size={15} /> Upload media</button></div></div>
              <div className="render-controls prominent-controls" aria-label="Frame rendering frequency controls">
                <label><span>Live camera FPS</span><input type="range" min="1" max="8" step="1" value={liveFps} onChange={event => setLiveFps(Number(event.target.value))} /><strong>{liveFps}</strong><small>live stream</small></label>
                <label><span>Video render FPS</span><input type="range" min="3" max="12" step="1" value={offlineFps} onChange={event => setOfflineFps(Number(event.target.value))} /><strong>{offlineFps}</strong><small>upload + recording</small></label>
              </div>
              <SessionLibrary items={sessionVideos} onSelect={acceptVideoResult} />
              <AnimatePresence mode="wait">{mode === 'camera' ? <motion.div key="camera" initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 8 }}><CameraPanel modelId={selectedModel} liveFps={liveFps} offlineFps={offlineFps} onResult={acceptResult} onProcessing={setProcessing} onError={setError} onVideo={acceptVideo} /></motion.div> : <motion.div key="upload" initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}><UploadPanel modelId={selectedModel} offlineFps={offlineFps} onResult={acceptResult} onVideoResult={acceptVideoResult} onProcessing={value => { if (value) { setResult(null); setVideoResult(null) }; setProcessing(value) }} onError={setError} /></motion.div>}</AnimatePresence>
            </section>
            <ResultGallery result={result} videoResult={videoResult} processing={processing} />
            </> : <ExerciseMode modelId={selectedModel} liveFps={liveFps} offlineFps={offlineFps} onError={setError} />}
          </main>
          <footer className="site-footer"><Brand /><span>Human Pose Estimation · Project 7</span><span>Idan · Lotem · Shahaf</span></footer>
          <AnimatePresence>{error && <motion.div className="toast error-toast" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}><CloudOff size={18} /><div><strong>Signal interrupted</strong><span>{error}</span></div><button onClick={() => setError(null)}><X size={15} /></button></motion.div>}</AnimatePresence>
          <AnimatePresence>{videoJob && <motion.div className={`toast job-toast ${videoJob.state}`} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}><Film size={18} /><div><strong>{videoJob.state === 'completed' ? 'Avatar sequence ready' : 'Rendering motion'}</strong><span>{videoJob.state === 'failed' ? videoJob.error : `${Math.round(videoJob.progress)}% · ${videoJob.filename}`}</span></div><button onClick={() => setVideoJob(null)}><ChevronDown size={16} /></button></motion.div>}</AnimatePresence>
        </motion.div>}
    </AnimatePresence>
  )
}

export default App
