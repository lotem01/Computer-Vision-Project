import { Download, Expand, Gauge, ScanLine, TimerReset, X } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useState } from 'react'
import type { PoseResult } from '../../types/domain'

const views = [
  { key: 'original', label: 'Source', tag: 'INPUT' },
  { key: 'skeleton', label: 'Pose map', tag: 'VISION' },
  { key: 'avatar', label: 'Avatar', tag: 'OUTPUT' },
] as const

export function ResultGallery({ result, processing }: { result: PoseResult | null; processing: boolean }) {
  const [expanded, setExpanded] = useState<(typeof views)[number]['key'] | null>(null)
  return (
    <section className="result-section" aria-labelledby="result-heading">
      <div className="section-heading">
        <div><span className="step-number">03</span><div><h2 id="result-heading">Motion decoded</h2><p>Source, structure, and expression—synchronized.</p></div></div>
        {result && <div className="result-metrics"><span><TimerReset size={14} /> {Math.round(result.timing.total_ms)} ms</span><span><ScanLine size={14} /> {result.detectedJoints}/{result.model.joint_count}</span><span><Gauge size={14} /> {Math.round((result.personBox?.confidence ?? 0) * 100)}%</span></div>}
      </div>
      <div className="result-grid">
        {views.map((view, index) => (
          <article className={`result-card ${view.key === 'avatar' ? 'featured' : ''}`} key={view.key}>
            <header><span><i>0{index + 1}</i>{view.label}</span><small>{view.tag}</small></header>
            <div className="result-frame">
              {result ? <motion.img key={`${result.frameId}-${view.key}`} initial={{ opacity: 0, scale: 1.025 }} animate={{ opacity: 1, scale: 1 }} src={result[view.key]} alt={`${view.label} result`} /> :
                <div className={`empty-visual empty-${index}`}><span className="empty-scan" /><div>{processing ? 'PROCESSING SIGNAL' : index === 0 ? 'AWAITING INPUT' : 'NO SIGNAL'}</div></div>}
              {processing && <div className="processing-shimmer" />}
              {result && <button className="expand-button" onClick={() => setExpanded(view.key)} aria-label={`Expand ${view.label}`}><Expand size={15} /></button>}
            </div>
            <footer>{result ? <><span className="signal"><i /> SIGNAL LOCKED</span><a href={result[view.key]} download={`poselab-${view.key}.jpg`}><Download size={13} /> Export</a></> : <span>—</span>}</footer>
          </article>
        ))}
      </div>
      <AnimatePresence>{expanded && result && <motion.div className="lightbox" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setExpanded(null)}><button><X /></button><motion.img initial={{ scale: .94 }} animate={{ scale: 1 }} src={result[expanded]} alt="Expanded result" /></motion.div>}</AnimatePresence>
    </section>
  )
}

