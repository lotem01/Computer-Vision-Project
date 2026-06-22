import { AnimatePresence, motion } from 'motion/react'
import { AlertTriangle, Check, Cpu, LoaderCircle, WifiOff } from 'lucide-react'
import { Brand } from '../../components/Brand'
import type { Readiness } from '../../types/domain'

const joints = [
  [50, 13], [40, 27], [60, 27], [32, 44], [68, 44], [25, 61], [75, 61],
  [43, 52], [57, 52], [40, 72], [60, 72], [37, 94], [63, 94],
]

export function ReadinessScreen({ data, connected, onEnter }: { data: Readiness | null; connected: boolean; onEnter: () => void }) {
  const ready = data?.readyCount ?? 0
  const failed = data?.models.filter(model => model.state === 'failed').length ?? 0
  const progress = data ? Math.round(((ready + failed) / data.totalCount) * 100) : 0

  return (
    <motion.main className="boot" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, scale: 1.02 }}>
      <div className="boot-orb boot-orb-a" /><div className="boot-orb boot-orb-b" />
      <header className="boot-header"><Brand /><span>Motion intelligence system · v1.0</span></header>
      <section className="boot-content">
        <div className="boot-copy">
          <span className="eyebrow"><span className="live-dot" /> SYSTEM INITIALIZATION</span>
          <h1>Preparing your<br /><em>motion engine.</em></h1>
          <p>Loading four specialized pose networks into memory and calibrating the visual pipeline for zero-delay switching.</p>
          <div className="boot-progress-row">
            <span>{connected ? 'Neural engines' : 'Waiting for local engine'}</span><strong>{connected ? `${progress}%` : '—'}</strong>
          </div>
          <div className="progress-track"><motion.div animate={{ width: `${progress}%` }} /></div>
        </div>
        <div className="body-viz" aria-label={`${ready} of 4 models ready`}>
          <div className="body-rings"><i /><i /><i /></div>
          <svg viewBox="0 0 100 112" role="img">
            <g className="body-lines">
              <path d="M50 13 L40 27 L32 44 L25 61 M50 13 L60 27 L68 44 L75 61 M40 27 L43 52 L40 72 L37 94 M60 27 L57 52 L60 72 L63 94 M40 27 L60 27 M43 52 L57 52" />
            </g>
            {joints.map(([x, y], index) => <circle key={index} className={index < Math.max(1, ready * 3.25) ? 'active' : ''} cx={x} cy={y} r="2.2" />)}
          </svg>
          <span className="scan-line" />
          <div className="viz-caption"><Cpu size={14} /> CPU inference · pre-warmed</div>
        </div>
      </section>
      <section className="model-boot-list">
        {(data?.models ?? Array.from({ length: 4 })).map((model, index) => {
          const state = model && 'state' in model ? model.state : 'pending'
          return (
            <motion.div className={`boot-model ${state}`} key={model && 'id' in model ? model.id : index} initial={{ y: 10, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: index * .07 }}>
              <span className="boot-index">0{index + 1}</span>
              <div><strong>{model && 'label' in model ? model.label : 'Awaiting engine'}</strong><small>{model && 'source' in model ? model.source : 'Connecting…'}</small></div>
              <span className="status-icon">
                {state === 'ready' ? <Check size={15} /> : state === 'failed' ? <AlertTriangle size={15} /> : <LoaderCircle size={15} />}
              </span>
            </motion.div>
          )
        })}
      </section>
      <footer className="boot-footer">
        <AnimatePresence mode="wait">
          {!connected ? <motion.span key="off" initial={{ opacity: 0 }} animate={{ opacity: 1 }}><WifiOff size={14} /> Start the Python backend to continue</motion.span> :
            data?.completed ? <motion.button key="ready" className="primary-button" onClick={onEnter} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>Enter studio <span>↗</span></motion.button> :
              <motion.span key="load" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>Optimizing model {Math.min(4, ready + failed + 1)} of 4</motion.span>}
        </AnimatePresence>
      </footer>
    </motion.main>
  )
}

