import { useEffect, useRef, type ReactNode } from 'react'

interface DialogProps {
  title: string
  size?: 'default' | 'wide'
  onClose: () => void
  actions?: ReactNode
  children: ReactNode
}

/**
 * Модальное окно на нативном <dialog>: ловушку фокуса, Esc и затемнение фона даёт браузер.
 * Открыто, пока смонтировано. Начальный фокус — на элемент с data-autofocus, иначе на само окно.
 */
export function Dialog({ title, size = 'default', onClose, actions, children }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (!dialog.open) dialog.showModal()
    // showModal сам фокусирует первый интерактивный элемент (обычно крестик) — переопределяем
    const initial = dialog.querySelector<HTMLElement>('[data-autofocus]') ?? dialog
    initial.focus()
    return () => dialog.close()
  }, [])

  return (
    <dialog
      ref={ref}
      className={size === 'wide' ? 'ui-dialog ui-dialog--wide' : 'ui-dialog'}
      aria-label={title}
      tabIndex={-1}
      onCancel={(event) => {
        // Esc: закрытие отдаём наружу, чтобы состояние (URL) оставалось источником правды
        event.preventDefault()
        onClose()
      }}
      onClick={(event) => {
        // Клик по затемнению: у <dialog> нет отступов, поэтому target === dialog только снаружи контента
        if (event.target === ref.current) onClose()
      }}
    >
      <div className="ui-dialog__inner">
        <header className="ui-dialog__header">
          <h2 className="ui-dialog__title">{title}</h2>
          <button type="button" className="ui-dialog__close" aria-label="Закрыть" onClick={onClose}>
            ×
          </button>
        </header>
        <div className="ui-dialog__body">{children}</div>
        {actions && <footer className="ui-dialog__actions">{actions}</footer>}
      </div>
    </dialog>
  )
}
