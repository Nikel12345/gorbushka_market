import type { ReactNode } from 'react'

interface SwitchProps {
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
  children: ReactNode
}

/** Переключатель вкл/выкл с подписью. Внутри — обычный checkbox (role=switch). */
export function Switch({ checked, onChange, disabled, children }: SwitchProps) {
  return (
    <label className={disabled ? 'ui-switch ui-switch--disabled' : 'ui-switch'}>
      <input
        type="checkbox"
        role="switch"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span className="ui-switch__track" aria-hidden="true" />
      <span className="ui-switch__label">{children}</span>
    </label>
  )
}
