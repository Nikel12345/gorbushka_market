import { useEffect, useRef } from 'react'

interface InfiniteScrollTriggerProps {
  onReach: () => void
  /** Пока идёт загрузка или грузить нечего — не срабатывает */
  disabled?: boolean
  /** Насколько заранее, до конца списка, начинать подгрузку */
  rootMargin?: string
}

/** Невидимая метка в конце списка: доскроллили до неё — onReach. */
export function InfiniteScrollTrigger({ onReach, disabled = false, rootMargin = '600px' }: InfiniteScrollTriggerProps) {
  const ref = useRef<HTMLDivElement>(null)
  const onReachRef = useRef(onReach)

  useEffect(() => {
    onReachRef.current = onReach
  })

  // Наблюдатель пересоздаётся после каждой загрузки: если метка всё ещё на экране
  // (большой монитор, мало карточек), он сразу сработает ещё раз
  useEffect(() => {
    const node = ref.current
    if (disabled || !node) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) onReachRef.current()
      },
      { rootMargin },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [disabled, rootMargin])

  return <div ref={ref} className="ui-infinite-trigger" aria-hidden="true" />
}
