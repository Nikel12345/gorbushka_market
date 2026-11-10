import { useId, useState, type CSSProperties, type FormEvent, type ReactNode } from 'react'
import { useNavigate } from 'react-router'
import { useReveal } from './hooks'
import { SearchIcon } from './icons'
import { catalogLink, scrollToCatalog } from './links'

/** Обёртка, которая плавно проявляется, когда доезжает до экрана */
export function Reveal({
  className,
  delay,
  children,
}: {
  className?: string
  /** Задержка в секундах — чтобы соседние блоки появлялись по очереди */
  delay?: number
  children: ReactNode
}) {
  const ref = useReveal<HTMLDivElement>()
  const style = delay ? ({ transitionDelay: `${delay}s` } as CSSProperties) : undefined
  return (
    <div ref={ref} className={className ? `sf-reveal ${className}` : 'sf-reveal'} style={style}>
      {children}
    </div>
  )
}

/** Поле поиска на первом экране: ведёт на ленту с ?q= (как поиск в шапке) */
export function HeroSearch({ className, placeholder }: { className: string; placeholder: string }) {
  const navigate = useNavigate()
  const id = useId()
  const [value, setValue] = useState('')

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const q = value.trim()
    navigate(catalogLink(q || undefined))
    if (!q) scrollToCatalog()
  }

  return (
    <form className={className} role="search" onSubmit={handleSubmit}>
      <label htmlFor={id} className="ui-sr-only">
        Что ищем
      </label>
      <SearchIcon />
      <input
        id={id}
        type="search"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder={placeholder}
        maxLength={200}
      />
      <button type="submit">Найти</button>
    </form>
  )
}
