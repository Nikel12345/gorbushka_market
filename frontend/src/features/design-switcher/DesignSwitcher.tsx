import { useId, type CSSProperties } from 'react'
import { designs, type DesignId } from './designs'
import './DesignSwitcher.css'

interface DesignSwitcherProps {
  value: DesignId
  onChange: (design: DesignId) => void
}

/** Панель под поиском: выбор варианта дизайна витрины. Нужна, пока заказчик выбирает вариант. */
export function DesignSwitcher({ value, onChange }: DesignSwitcherProps) {
  const labelId = useId()
  const name = useId()

  return (
    <div className="design-switcher">
      <div className="design-switcher__inner">
        <div className="design-switcher__panel" role="radiogroup" aria-labelledby={labelId}>
          <span id={labelId} className="design-switcher__label">
            Дизайн
          </span>
          {designs.map((design) => {
            const active = design.id === value
            const swatch = { '--swatch-bg': design.swatch[0], '--swatch-accent': design.swatch[1] } as CSSProperties
            return (
              <label
                key={design.id}
                className={active ? 'design-switcher__option design-switcher__option--active' : 'design-switcher__option'}
              >
                <input
                  type="radio"
                  name={name}
                  value={design.id}
                  checked={active}
                  onChange={() => onChange(design.id)}
                  className="ui-sr-only"
                />
                <span className="design-switcher__swatch" style={swatch} aria-hidden="true" />
                {design.title}
              </label>
            )
          })}
        </div>
      </div>
    </div>
  )
}
