import { useState, type KeyboardEvent } from 'react'
import { getFieldErrors } from '@/shared/api'
import { Button, FieldError } from '@/shared/ui'
import './catalogAdmin.css'

interface InlineCreateFieldProps<T> {
  /** Подпись поля для читалок: «Новое значение характеристики «Цвет»» */
  label: string
  placeholder?: string
  /** Создаёт запись на сервере; бросает ошибку API */
  create: (text: string) => Promise<T>
  /** Поле сериализатора, чьи ошибки показать под строкой (value, name) */
  field: string
  onCreated: (item: T) => void
  onCancel: () => void
}

/**
 * Добавить запись справочника одной строкой: значение характеристики, характеристику.
 * Не <form> — живёт и внутри других форм; Enter добавляет, Esc отменяет.
 */
export function InlineCreateField<T>({ label, placeholder, create, field, onCreated, onCancel }: InlineCreateFieldProps<T>) {
  const [text, setText] = useState('')
  const [errors, setErrors] = useState<string[]>()
  const [saving, setSaving] = useState(false)

  async function submit() {
    const trimmed = text.trim()
    if (!trimmed) {
      setErrors(['Введите название.'])
      return
    }
    setSaving(true)
    setErrors(undefined)
    try {
      onCreated(await create(trimmed))
    } catch (error) {
      const fieldErrors = getFieldErrors(error)
      setErrors(fieldErrors[field] ?? fieldErrors.non_field_errors ?? Object.values(fieldErrors)[0])
      setSaving(false)
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter') {
      event.preventDefault()
      submit()
    } else if (event.key === 'Escape') {
      // Внутри диалога Esc закрыл бы весь диалог
      event.preventDefault()
      onCancel()
    }
  }

  return (
    <div className="inline-create">
      <div className="inline-create__row">
        <input
          className="ui-input"
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          aria-label={label}
          aria-invalid={Boolean(errors)}
          maxLength={100}
          disabled={saving}
          autoFocus
        />
        <Button variant="primary" onClick={submit} disabled={saving}>
          {saving ? 'Добавляем…' : 'Добавить'}
        </Button>
        <Button variant="text" onClick={onCancel} disabled={saving}>
          Отмена
        </Button>
      </div>
      <FieldError messages={errors} />
    </div>
  )
}
