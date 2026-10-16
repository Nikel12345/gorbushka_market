import { useRef, type ReactNode } from 'react'
import { Button, type ButtonVariant } from './Button'

interface FileButtonProps {
  accept?: string
  variant?: ButtonVariant
  disabled?: boolean
  /** Можно выбрать несколько файлов сразу */
  multiple?: boolean
  className?: string
  onSelect: (files: File[]) => void
  children: ReactNode
}

/** Кнопка выбора файла вместо системного <input type="file">. */
export function FileButton({
  accept,
  variant = 'default',
  disabled,
  multiple,
  className,
  onSelect,
  children,
}: FileButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  return (
    <>
      <Button variant={variant} className={className} disabled={disabled} onClick={() => inputRef.current?.click()}>
        {children}
      </Button>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        hidden
        onChange={(event) => {
          const files = [...(event.target.files ?? [])]
          // Сбрасываем, чтобы повторный выбор того же файла тоже срабатывал
          event.target.value = ''
          if (files.length > 0) onSelect(files)
        }}
      />
    </>
  )
}
