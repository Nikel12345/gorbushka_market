import { useState } from 'react'
import { ProductImage } from '@/entities/product'
import { PRODUCT_PHOTOS_MAX } from '@/shared/api'
import { useObjectUrl } from '@/shared/lib'
import { FieldError, FileButton } from '@/shared/ui'
import { photosFromFiles, type PhotoItem } from './productPhotos'
import './productFields.css'

interface ProductPhotosFieldProps {
  value: PhotoItem[]
  onChange: (value: PhotoItem[]) => void
  errors?: string[]
}

function move(list: PhotoItem[], from: number, to: number): PhotoItem[] {
  const next = [...list]
  const [item] = next.splice(from, 1)
  next.splice(to, 0, item)
  return next
}

/**
 * Фото товара в форме: добавить несколько, убрать, поменять порядок (стрелками или
 * перетаскиванием). Первое — обложка. Сохраняется вместе с остальными полями.
 * Заголовок и счётчик — у карточки, в которой стоит поле.
 */
export function ProductPhotosField({ value, onChange, errors }: ProductPhotosFieldProps) {
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [notice, setNotice] = useState<string>()
  const free = PRODUCT_PHOTOS_MAX - value.length

  function add(files: File[]) {
    const accepted = files.slice(0, free)
    setNotice(
      accepted.length < files.length
        ? `Добавлено ${accepted.length} из ${files.length}: у товара может быть не больше ${PRODUCT_PHOTOS_MAX} фото.`
        : undefined,
    )
    onChange([...value, ...photosFromFiles(accepted)])
  }

  function remove(index: number) {
    setNotice(undefined)
    onChange(value.filter((_, i) => i !== index))
  }

  return (
    <div className="product-photos">
      <ul className="product-photos__grid">
        {value.map((photo, index) => (
          <li
            key={photo.key}
            className={dragIndex === index ? 'product-photos__item product-photos__item--dragging' : 'product-photos__item'}
            draggable
            onDragStart={() => setDragIndex(index)}
            onDragEnd={() => setDragIndex(null)}
            onDragOver={(event) => {
              event.preventDefault()
              if (dragIndex === null || dragIndex === index) return
              onChange(move(value, dragIndex, index))
              setDragIndex(index)
            }}
          >
            <PhotoPreview photo={photo} />
            {index === 0 && <span className="product-photos__cover">Обложка</span>}
            <div className="product-photos__tools">
              <button
                type="button"
                onClick={() => onChange(move(value, index, index - 1))}
                disabled={index === 0}
                aria-label="Левее"
                title="Левее"
              >
                ‹
              </button>
              {index > 0 && (
                <button
                  type="button"
                  onClick={() => onChange(move(value, index, 0))}
                  aria-label="Сделать обложкой"
                  title="Сделать обложкой"
                >
                  ★
                </button>
              )}
              <button
                type="button"
                onClick={() => onChange(move(value, index, index + 1))}
                disabled={index === value.length - 1}
                aria-label="Правее"
                title="Правее"
              >
                ›
              </button>
              <button
                type="button"
                className="product-photos__remove"
                onClick={() => remove(index)}
                aria-label="Убрать фото"
                title="Убрать фото"
              >
                ✕
              </button>
            </div>
          </li>
        ))}
        {free > 0 && (
          <li>
            <FileButton accept="image/*" multiple onSelect={add} className="product-photos__add">
              <span className="product-photos__plus" aria-hidden="true">
                +
              </span>
              {value.length === 0 ? 'Добавить фото' : 'Ещё фото'}
            </FileButton>
          </li>
        )}
      </ul>

      <span className="ui-field__hint">
        {value.length > 1
          ? 'Первое фото — обложка. Порядок меняется стрелками или перетаскиванием.'
          : 'JPG, PNG или WebP. Можно выбрать несколько сразу или добавить позже.'}
      </span>
      {notice && <span className="ui-field__hint">{notice}</span>}
      <FieldError messages={errors} />
    </div>
  )
}

function PhotoPreview({ photo }: { photo: PhotoItem }) {
  const fileUrl = useObjectUrl(photo.kind === 'new' ? photo.file : null)
  return (
    <ProductImage
      src={photo.kind === 'new' ? fileUrl : photo.url}
      alt={photo.kind === 'new' ? photo.file.name : ''}
      className="product-photos__image"
    />
  )
}
