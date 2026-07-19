import { Activity, Award, Dumbbell, Play, RotateCcw, UploadCloud, Video, VideoOff } from 'lucide-react'
import { ChangeEvent, useCallback, useEffect, useRef, useState } from 'react'
import { motion } from 'motion/react'
import { api } from '../../api/client'
import type { ExerciseCompareResult, ExerciseInstructor, ExerciseSummary } from '../../types/domain'

interface Props {
  modelId: string
  liveFps: number
  offlineFps: number
  onError: (message: string) => void
}

export function ExerciseMode({ modelId, liveFps, offlineFps, onError }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const timerRef = useRef<number | undefined>(undefined)
  const instructorTimerRef = useRef<number | undefined>(undefined)
  const currentFrameRef = useRef(0)
  const awaitingRef = useRef(false)
  const samplesRef = useRef<ExerciseCompareResult[]>([])
  const [library, setLibrary] = useState<ExerciseInstructor[]>([])
  const [instructor, setInstructor] = useState<ExerciseInstructor | null>(null)
  const [cameraActive, setCameraActive] = useState(false)
  const [started, setStarted] = useState(false)
  const [ended, setEnded] = useState(false)
  const [currentFrame, setCurrentFrame] = useState(0)
  const [latest, setLatest] = useState<ExerciseCompareResult | null>(null)
  const [summary, setSummary] = useState<ExerciseSummary | null>(null)

  useEffect(() => {
    api.exerciseInstructors().then(data => setLibrary(data.items)).catch(error => onError((error as Error).message))
  }, [onError])

  useEffect(() => {
    if (!instructor || !['queued', 'processing'].includes(instructor.state)) return
    const timer = window.setTimeout(async () => {
      try {
        const next = await api.exerciseInstructor(instructor.id)
        setInstructor(next)
        if (next.state === 'completed') {
          setLibrary(items => items.some(item => item.id === next.id) ? items : [next, ...items])
        }
        if (next.state === 'failed' && next.error) onError(next.error)
      } catch (error) {
        onError((error as Error).message)
      }
    }, 700)
    return () => clearTimeout(timer)
  }, [instructor, onError])

  const frameBlob = useCallback(() => new Promise<Blob | null>(resolve => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas || !video.videoWidth) return resolve(null)
    canvas.width = Math.min(640, video.videoWidth)
    canvas.height = Math.round(canvas.width * video.videoHeight / video.videoWidth)
    canvas.getContext('2d')!.drawImage(video, 0, 0, canvas.width, canvas.height)
    canvas.toBlob(resolve, 'image/jpeg', .76)
  }), [])

  const resetSession = () => {
    window.clearTimeout(timerRef.current)
    window.clearInterval(instructorTimerRef.current)
    currentFrameRef.current = 0
    samplesRef.current = []
    setCurrentFrame(0)
    setLatest(null)
    setSummary(null)
    setStarted(false)
    setEnded(false)
  }

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false })
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      setCameraActive(true)
      resetSession()
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Camera permission was not granted.')
    }
  }

  const stopCamera = () => {
    const stream = videoRef.current?.srcObject as MediaStream | null
    stream?.getTracks().forEach(track => track.stop())
    if (videoRef.current) videoRef.current.srcObject = null
    setCameraActive(false)
    resetSession()
  }

  const finish = useCallback(async () => {
    window.clearTimeout(timerRef.current)
    window.clearInterval(instructorTimerRef.current)
    setEnded(true)
    try {
      setSummary(await api.exerciseSummary(samplesRef.current))
    } catch (error) {
      onError((error as Error).message)
    }
  }, [onError])

  const advanceInstructor = useCallback((readyInstructor: ExerciseInstructor) => {
    window.clearInterval(instructorTimerRef.current)
    instructorTimerRef.current = window.setInterval(() => {
      currentFrameRef.current += 1
      if (currentFrameRef.current >= readyInstructor.frameCount) {
        void finish()
        return
      }
      setCurrentFrame(currentFrameRef.current)
    }, Math.max(80, Math.round(1000 / readyInstructor.fps)))
  }, [finish])

  const compareLoop = useCallback(async () => {
    window.clearTimeout(timerRef.current)
    if (!cameraActive || !instructor || instructor.state !== 'completed' || ended) return
    timerRef.current = window.setTimeout(async () => {
      if (awaitingRef.current) return compareLoop()
      const blob = await frameBlob()
      if (!blob) return compareLoop()
      awaitingRef.current = true
      try {
        const targetFrame = started ? currentFrameRef.current : 0
        const result = await api.compareExerciseFrame(instructor.id, targetFrame, modelId, blob)
        setLatest(result)
        if (started) samplesRef.current.push(result)
        if (!started && result.matchedInitial) {
          setStarted(true)
          samplesRef.current = [result]
          advanceInstructor(instructor)
        }
      } catch (error) {
        onError((error as Error).message)
      } finally {
        awaitingRef.current = false
        compareLoop()
      }
    }, Math.max(125, Math.round(1000 / liveFps)))
  }, [advanceInstructor, cameraActive, ended, frameBlob, instructor, liveFps, modelId, onError, started])

  useEffect(() => {
    compareLoop()
    return () => window.clearTimeout(timerRef.current)
  }, [compareLoop])

  useEffect(() => () => stopCamera(), [])

  const upload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    resetSession()
    try {
      const created = await api.submitExerciseInstructor(file, modelId, Math.min(offlineFps, 8))
      setInstructor(created)
      setLibrary(items => items.some(item => item.id === created.id) ? items : [created, ...items])
    } catch (error) {
      onError((error as Error).message)
    }
  }

  const ready = instructor?.state === 'completed'
  const instructorFrame = ready && instructor.frames[currentFrame] ? instructor.frames[currentFrame] : null
  const average = samplesRef.current.length ? Math.round(samplesRef.current.reduce((sum, item) => sum + item.score, 0) / samplesRef.current.length) : 0
  const closeCount = latest?.jointFeedback.filter(item => item.close).length ?? 0

  return (
    <section className="exercise-section" id="exercise">
      <div className="section-heading">
        <div><span className="step-number">EX</span><div><h2>Exercise Mode</h2><p>Follow an instructor pose sequence with live joint-level feedback.</p></div></div>
        <div className="result-metrics"><span><Activity size={14} /> {latest ? `${Math.round(latest.score)} live` : 'WAITING'}</span><span><Award size={14} /> {average} avg</span></div>
      </div>

      <div className="exercise-grid">
        <aside className="exercise-sidebar">
          <label className="exercise-upload">
            <UploadCloud size={19} />
            <span>Upload instructor video</span>
            <small>processed once · reused later</small>
            <input type="file" accept="video/*" onChange={upload} hidden />
          </label>
          {instructor && instructor.state !== 'completed' && (
            <div className="exercise-processing"><strong>{instructor.state}</strong><span>{Math.round(instructor.progress)}%</span><div className="progress-track"><motion.div animate={{ width: `${instructor.progress}%` }} /></div></div>
          )}
          <div className="exercise-library">
            <span>Instructor library</span>
            {library.length === 0 ? <p>No processed videos yet.</p> : library.map(item => (
              <button key={item.id} type="button" className={instructor?.id === item.id ? 'active' : ''} onClick={() => { resetSession(); setInstructor(item) }}>
                <Dumbbell size={14} /><span>{item.filename}</span><small>{item.frameCount || 0} poses {item.cached ? '· cached' : ''}</small>
              </button>
            ))}
          </div>
        </aside>

        <div className="exercise-stage">
          <video ref={videoRef} className="exercise-capture-source" muted playsInline autoPlay />
          <canvas ref={canvasRef} hidden />
          <div className="exercise-hud">
            <strong>{ready ? started ? ended ? 'SESSION COMPLETE' : 'FOLLOW THE MOVE' : 'MATCH INITIAL POSE' : 'LOAD INSTRUCTOR'}</strong>
            <span>{ready ? `Frame ${Math.min(currentFrame + 1, instructor.frameCount)} / ${instructor.frameCount}` : 'Upload or select a processed instructor'}</span>
          </div>
          <div className="exercise-previews">
            <article>
              <header><span>Instructor skeleton</span><small>{ready ? `${instructor.fps.toFixed(1)} FPS` : 'LOCKED'}</small></header>
              <div className="exercise-frame">{instructorFrame ? <img src={instructorFrame.skeletonUrl} alt="Instructor pose skeleton" /> : <div className="empty-visual"><div>AWAITING INSTRUCTOR</div></div>}</div>
            </article>
            <article>
              <header><span>Your live pose</span><small>{closeCount} joints aligned</small></header>
              <div className="exercise-frame">{latest ? <img src={latest.userSkeleton} alt="Live user skeleton feedback" /> : <div className={`camera-stage ${cameraActive ? 'active' : ''}`}>{cameraActive ? <div className="camera-empty"><span>LIVE FEEDBACK</span><h3>Align with the instructor</h3><p>Your colored skeleton will appear after the first comparison.</p></div> : <button className="primary-button" disabled={!ready} onClick={startCamera}><Video size={15} /> Start exercise camera</button>}</div>}</div>
            </article>
          </div>
          <div className="exercise-controls">
            {cameraActive ? <button onClick={stopCamera}><VideoOff size={15} /> Stop camera</button> : <button disabled={!ready} onClick={startCamera}><Video size={15} /> Start camera</button>}
            <button disabled={!ready} onClick={resetSession}><RotateCcw size={15} /> Reset session</button>
            <button disabled={!ready || !cameraActive || ended} onClick={() => { if (!started) setCurrentFrame(0) }}><Play size={15} /> Waiting for initial match</button>
          </div>
          <div className="joint-strip">
            {(latest?.jointFeedback ?? []).map(joint => <span key={joint.name} className={joint.close ? 'good' : 'bad'}>{joint.name.replace('_', ' ')} {Math.round(joint.score)}</span>)}
          </div>
          {summary && (
            <div className="exercise-summary">
              <h3>Performance score: {Math.round(summary.averageScore)}</h3>
              <div><strong>Best joints</strong>{summary.bestJoints.map(joint => <span key={joint.name}>{joint.name.replace('_', ' ')} · {Math.round(joint.score)}</span>)}</div>
              <div><strong>Improve next</strong>{summary.improveJoints.map(joint => <span key={joint.name}>{joint.name.replace('_', ' ')} · {Math.round(joint.score)}</span>)}</div>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
