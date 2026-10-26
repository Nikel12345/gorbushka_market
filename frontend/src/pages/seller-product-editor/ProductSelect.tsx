import { useEffect, useId, useRef, useState, type CSSProperties, type KeyboardEvent, type ToggleEvent } from 'react'
import { ProductImage } from '@/entities/product'
import type { Product } from '@/shared/api'
import { formatPrice } from '@/shared/lib'
import { Chip } from '@/shared/ui'
import './ProductSelect.css'

interface ProductSelectProps {
  options: Product[]
  value: Product | undefined
  onChange: (product: Product) => void
  /** Почему товар нельзя выбрать; undefined — можно */
  unavailable: (product: Product) => string | undefined
  /** Текст на кнопке, пока ничего не выбрано */
  placeholder: string
  /** id подписи поля */
  labelId: string
  /** Список перезапрашивается — старые товары видны, но приглушены */
  loading?: boolean
  disabled?: boolean
}

/** Список не выше этого; если снизу места меньше, а сверху больше — открывается вверх */
const LIST_MAX_HEIGHT = 380
const LIST_GAP = 4
const VIEWPORT_MARGIN = 8

/** popover живёт в верхнем слое и не знает о кнопке — ставим его к ней вплотную, во всю её ширину */
function placeUnder(button: HTMLElement): CSSProperties {
  const rect = button.getBoundingClientRect()
  const below = window.innerHeight - rect.bottom - LIST_GAP - VIEWPORT_MARGIN
  const above = rect.top - LIST_GAP - VIEWPORT_MARGIN
  const up = below < 240 && above > below
  return {
    left: rect.left,
    width: rect.width,
    maxHeight: Math.min(LIST_MAX_HEIGHT, up ? above : below),
    ...(up ? { bottom: window.innerHeight - rect.top + LIST_GAP } : { top: rect.bottom + LIST_GAP }),
  }
}

/**
 * Выбор товара с превью: кнопка в виде поля, под ней — найденные товары с фото, категорией, ценой
 * и наличием. Список — нативный popover: закрывается кликом мимо и Esc, стрелки ходят по товарам.
 */
export function ProductSelect({
  options,
  value,
  onChange,
  unavailable,
  placeholder,
  labelId,
  loading = false,
  disabled = false,
}: ProductSelectProps) {
  const listId = useId()
  const buttonRef = useRef<HTMLButtonElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  const [position, setPosition] = useState<CSSProperties>()

  // Пока открыт — едет вместе с кнопкой при прокрутке страницы и смене размера окна
  useEffect(() => {
    if (!open) return
    const update = () => buttonRef.current && setPosition(placeUnder(buttonRef.current))
    window.addEventListener('scroll', update, true)
    window.addEventListener('resize', update)
    return () => {
      window.removeEventListener('scroll', update, true)
      window.removeEventListener('resize', update)
    }
  }, [open])

  function handleBeforeToggle(event: ToggleEvent<HTMLDivElement>) {
    if (event.newState === 'open' && buttonRef.current) setPosition(placeUnder(buttonRef.current))
  }

  function handleToggle(event: ToggleEvent<HTMLDivElement>) {
    const isOpen = event.newState === 'open'
    setOpen(isOpen)
    if (!isOpen) return
    // Фокус — на выбранный товар, иначе на первый доступный
    const list = listRef.current
    const target =
      list?.querySelector<HTMLButtonElement>('[aria-selected="true"]:not(:disabled)') ??
      list?.querySelector<HTMLButtonElement>('button:not(:disabled)')
    target?.focus({ preventScroll: true })
    target?.scrollIntoView({ block: 'nearest' })
  }

  function handleListKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const items = [...(listRef.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') ?? [])]
    if (items.length === 0) return
    const index = items.indexOf(document.activeElement as HTMLButtonElement)
    let next: number | undefined
    if (event.key === 'ArrowDown') next = Math.min(index + 1, items.length - 1)
    else if (event.key === 'ArrowUp') next = Math.max(index - 1, 0)
    else if (event.key === 'Home') next = 0
    else if (event.key === 'End') next = items.length - 1
    if (next === undefined) return
    event.preventDefault()
    items[next].focus()
  }

  function pick(product: Product) {
    onChange(product)
    listRef.current?.hidePopover()
    // Сам popover возвращает фокус, только если кнопка была в фокусе (Safari по клику её не фокусирует)
    buttonRef.current?.focus()
  }

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className="ui-input product-select__button"
        popoverTarget={listId}
        aria-haspopup="listbox"
        aria-labelledby={labelId}
        disabled={disabled}
      >
        {value ? (
          <>
            <ProductImage src={value.image} alt="" className="product-select__image product-select__image--small" />
            <span className="product-select__text">
              <span className="product-select__title">{value.title}</span>
              <span className="product-select__meta">{formatPrice(value.price)}</span>
            </span>
          </>
        ) : (
          <span className="product-select__placeholder">{placeholder}</span>
        )}
        <span className="product-select__chevron" aria-hidden="true" />
      </button>

      <div
        ref={listRef}
        id={listId}
        popover="auto"
        role="listbox"
        aria-labelledby={labelId}
        className={loading ? 'product-select__list product-select__list--dimmed' : 'product-select__list'}
        style={position}
        onBeforeToggle={handleBeforeToggle}
        onToggle={handleToggle}
        onKeyDown={handleListKeyDown}
      >
        {options.map((item) => {
          const reason = unavailable(item)
          const selected = item.id === value?.id
          const meta = [item.category?.name, formatPrice(item.price)].filter(Boolean).join(' · ')
          let status = <span className="product-select__stock">{item.quantity} шт.</span>
          if (reason) status = <Chip>{reason}</Chip>
          else if (item.quantity === 0) status = <Chip tone="warning">нет в наличии</Chip>

          return (
            <button
              key={item.id}
              type="button"
              role="option"
              aria-selected={selected}
              disabled={Boolean(reason)}
              className={selected ? 'product-select__option product-select__option--selected' : 'product-select__option'}
              onClick={() => pick(item)}
            >
              <ProductImage src={item.image} alt="" className="product-select__image" />
              <span className="product-select__text">
                <span className="product-select__title">{item.title}</span>
                <span className="product-select__meta">{meta}</span>
              </span>
              {status}
            </button>
          )
        })}
      </div>
    </>
  )
}
