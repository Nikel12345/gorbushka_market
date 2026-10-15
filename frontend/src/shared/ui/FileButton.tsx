import { useRef, type ReactNode } from 'react'
import { Button, type ButtonVariant } from './Button'

interface FileButtonProps {
  accept?: string
  variant?: ButtonVariant
  disabled?: boolean
  onSelect: (file: File) => void
  children: ReactNode
}

/** Кнопка выбора файла вместо системного <input type="file">. */
export function FileButton({ accept, variant = 'default', disabled, onSelect, children }: FileButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  return (
    <>
      <Button variant={variant} disabled={disabled} onClick={() => inputRef.current?.click()}>
        {children}
      </Button>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0]
          // Сбрасываем, чтобы повторный выбор того же файла тоже срабатывал
          event.target.value = ''
          if (file) onSelect(file)
        }}
      />
    </>
  )
}
