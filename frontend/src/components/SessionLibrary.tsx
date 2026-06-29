import { Film, RotateCcw } from 'lucide-react'
import type { DecodedVideoResult } from '../types/domain'

interface Props {
  items: DecodedVideoResult[]
  onSelect: (item: DecodedVideoResult) => void
}

export function SessionLibrary({ items, onSelect }: Props) {
  return (
    <div className={`session-cache session-library ${items.length ? 'has-items' : 'is-empty'}`}>
      <span>Rendered this session</span>
      {items.length ? (
        <div>
          {items.map(item => (
            <button key={item.jobId} type="button" onClick={() => onSelect(item)}>
              <Film size={13} /> {item.filename}
            </button>
          ))}
        </div>
      ) : (
        <p><RotateCcw size={13} /> Render or record a video and it will appear here for instant replay.</p>
      )}
    </div>
  )
}
