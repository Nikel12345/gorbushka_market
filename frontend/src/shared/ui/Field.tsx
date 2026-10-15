import type { ReactNode } from 'react'
import { FieldError } from './FieldError'

interface FieldProps {
  label: string
  errors?: string[]
  hint?: string
  children: ReactNode
}

/** Подпись + контрол (input/textarea/select с классом ui-input) + ошибки. */
export function Field({ label, errors, hint, children }: FieldProps) {
  return (
    <label className="ui-field">
      <span className="ui-field__label">{label}</span>
      {children}
      {hint && !errors?.length && <span className="ui-field__hint">{hint}</span>}
      <FieldError messages={errors} />
    </label>
  )
}
