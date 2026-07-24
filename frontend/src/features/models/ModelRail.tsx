import { Check, TriangleAlert } from 'lucide-react'
import { motion } from 'motion/react'
import type { ModelMetadata } from '../../types/domain'

export function ModelRail({ models, selected, onSelect }: { models: ModelMetadata[]; selected: string; onSelect: (id: string) => void }) {
  return (
    <section className="model-section" aria-labelledby="model-heading">
      <div className="section-heading">
        <div><span className="step-number">01</span><div><h2 id="model-heading">Choose intelligence</h2><p>Every engine sees motion differently.</p></div></div>
        <span className="resident-label"><span /> {models.filter(m => m.state === 'ready').length} engines resident</span>
      </div>
      <div className="model-grid">
        {models.map((model, index) => {
          const active = model.id === selected
          const disabled = model.state !== 'ready'
          return (
            <motion.button whileHover={disabled ? undefined : { y: -4 }} whileTap={disabled ? undefined : { scale: .985 }} key={model.id} className={`model-card ${active ? 'active' : ''} ${disabled ? 'disabled' : ''}`} onClick={() => !disabled && onSelect(model.id)} disabled={disabled}>
              <div className="model-card-top"><span>0{index + 1}</span><i>{disabled ? <TriangleAlert size={13} /> : <Check size={13} />}{disabled ? ' unavailable' : ' ready'}</i></div>
              <div className="mini-pose" aria-hidden="true"><span /><span /><span /><span /><span /></div>
              <h3>{model.label}</h3><p>{model.description}</p>
              <div className="model-stats"><span><strong>{model.joint_count}</strong> joints</span><span>{model.source}</span></div>
              {active && <motion.div className="active-edge" layoutId="active-model" />}
            </motion.button>
          )
        })}
      </div>
    </section>
  )
}

