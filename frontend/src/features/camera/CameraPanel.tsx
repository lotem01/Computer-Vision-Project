import { Camera, CircleStop, Radio, RefreshCw, Video, VideoOff } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../../api/client'
import type { PoseResult } from '../../types/domain'

interface Props {
  modelId: string
  liveFps: number
  offlineFps: number
  onResult: (result: PoseResult) => void
  onProcessing: (value: boolean) => void
  onError: (message: string) => void
  onVideo: (file: File) => void
}

export function CameraPanel({ modelId, liveFps, offlineFps, onResult, onProcessing, onError, onVideo }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const timerRef = useRef<number | undefined>(undefined)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const frameRef = useRef(0)
  const awaitingRef = useRef(false)
  const activeRef = useRef(false)
  const modelRef = useRef(modelId)
  const liveFpsRef = useRef(liveFps)
  const [active, setActive] = useState(false)
  const [recording, setRecording] = useState(false)
  modelRef.current = modelId
  liveFpsRef.current = liveFps

  const frameBlob = useCallback(() => new Promise<Blob | null>(resolve => {
    const video = videoRef.current; const canvas = canvasRef.current
    if (!video || !canvas || !video.videoWidth) return resolve(null)
    canvas.width = Math.min(720, video.videoWidth); canvas.height = Math.round(canvas.width * video.videoHeight / video.videoWidth)
    canvas.getContext('2d')!.drawImage(video, 0, 0, canvas.width, canvas.height)
    canvas.toBlob(resolve, 'image/jpeg', .78)
  }), [])

  const scheduleFrame = useCallback(() => {
    window.clearTimeout(timerRef.current)
    timerRef.current = window.setTimeout(async () => {
      const socket = socketRef.current
      if (!activeRef.current || !socket || socket.readyState !== WebSocket.OPEN || awaitingRef.current) return scheduleFrame()
      const blob = await frameBlob(); if (!blob) return scheduleFrame()
      awaitingRef.current = true; frameRef.current += 1
      const reader = new FileReader(); reader.onload = () => socket.send(JSON.stringify({ frameId: frameRef.current, modelId: modelRef.current, image: reader.result })); reader.readAsDataURL(blob)
    }, Math.max(125, Math.round(1000 / liveFpsRef.current)))
  }, [frameBlob])

  useEffect(() => { if (active) scheduleFrame(); return () => clearTimeout(timerRef.current) }, [active, scheduleFrame])
  useEffect(() => () => { socketRef.current?.close(); videoRef.current?.srcObject && (videoRef.current.srcObject as MediaStream).getTracks().forEach(track => track.stop()) }, [])

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false })
      if (videoRef.current) { videoRef.current.srcObject = stream; await videoRef.current.play() }
      const socket = api.liveSocket(); socketRef.current = socket
      socket.onmessage = event => {
        awaitingRef.current = false
        const message = JSON.parse(event.data)
        if (message.type === 'result') onResult(message.data)
        if (message.type === 'error') onError(message.message ?? 'Live frame could not be decoded.')
        scheduleFrame()
      }
      socket.onerror = () => { awaitingRef.current = false; onError('Live connection was interrupted.') }
      activeRef.current = true; setActive(true)
    } catch (error) { onError(error instanceof Error ? error.message : 'Camera permission was not granted.') }
  }

  const stop = () => {
    socketRef.current?.close(); socketRef.current = null
    const stream = videoRef.current?.srcObject as MediaStream | null; stream?.getTracks().forEach(track => track.stop())
    if (videoRef.current) videoRef.current.srcObject = null
    activeRef.current = false; setActive(false); setRecording(false); awaitingRef.current = false
  }

  const capture = async () => {
    const blob = await frameBlob(); if (!blob) return
    onProcessing(true)
    try { onResult(await api.inferImage(blob, modelId)) } catch (error) { onError((error as Error).message) } finally { onProcessing(false) }
  }

  const toggleRecord = () => {
    if (!recording) {
      const stream = videoRef.current?.srcObject as MediaStream
      if (!stream) return onError('Start the camera before recording motion.')
      chunksRef.current = []
      const recorder = new MediaRecorder(stream, { mimeType: MediaRecorder.isTypeSupported('video/webm;codecs=vp9') ? 'video/webm;codecs=vp9' : 'video/webm' })
      recorder.ondataavailable = event => event.data.size && chunksRef.current.push(event.data)
      recorder.onstop = () => onVideo(new File(chunksRef.current, 'camera-motion.webm', { type: 'video/webm' }))
      recorder.start(); recorderRef.current = recorder; setRecording(true)
    } else { recorderRef.current?.stop(); setRecording(false) }
  }

  return (
    <div className="input-panel camera-panel">
      <div className={`camera-stage ${active ? 'active' : ''}`}>
        <video ref={videoRef} muted playsInline autoPlay /> <canvas ref={canvasRef} hidden />
        {!active && <div className="camera-empty"><div className="camera-lens"><Video size={28} /></div><span>LIVE MOTION CAPTURE</span><h3>Bring your pose to life</h3><p>Your camera stays on this computer. Frames are processed by the local engine.</p><button className="primary-button" onClick={start}><Video size={15} /> Enable camera</button></div>}
        {active && <><div className="camera-corners"><i /><i /><i /><i /></div><span className="live-badge"><Radio size={12} /> LIVE</span><span className="fps-badge">{liveFps} FPS · LOCAL</span></>}
      </div>
      <div className="camera-controls">
        <button disabled={!active} onClick={capture}><Camera size={17} /><span>Capture still</span></button>
        <button disabled={!active} className={recording ? 'recording' : ''} onClick={toggleRecord}>{recording ? <CircleStop size={17} /> : <span className="record-dot" />}<span>{recording ? 'Stop recording' : 'Record motion'}</span></button>
        <button disabled={!active} onClick={stop}><VideoOff size={17} /><span>End camera</span></button>
        <button disabled={!active} onClick={() => { stop(); setTimeout(start, 100) }} aria-label="Restart camera"><RefreshCw size={17} /></button>
      </div>
      <p className="recording-hint">Recorded clips render at {offlineFps} FPS and open automatically in the Source / Pose map / Avatar previews when processing finishes.</p>
    </div>
  )
}
