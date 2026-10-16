import { useEffect, useState } from 'react'

/**
 * Сколько колонок сейчас у CSS-сетки (repeat(auto-fill, …) меняет их по ширине).
 * Элемент передаётся через callback-ref: `const [grid, setGrid] = useState(null)`, `ref={setGrid}`.
 * 0 — пока не измерено.
 */
export function useGridColumns(element: HTMLElement | null): number {
  const [columns, setColumns] = useState(0)

  useEffect(() => {
    if (!element) return
    const measure = () => {
      const template = getComputedStyle(element).gridTemplateColumns
      setColumns(template && template !== 'none' ? template.split(' ').length : 0)
    }
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(element)
    return () => observer.disconnect()
  }, [element])

  return columns
}
