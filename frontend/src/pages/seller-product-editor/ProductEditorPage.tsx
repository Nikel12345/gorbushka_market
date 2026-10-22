import { useCallback, useState, type ReactNode } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router'
import {
  BackButton,
  CategorySelect,
  GroupProducts,
  useBack,
  useCategories,
  useCharacteristics,
  useSeller,
  type BackState,
} from '@/features/seller'
import {
  adminApi,
  ApiError,
  getErrorMessage,
  getFieldErrors,
  PRODUCT_PHOTOS_MAX,
  type FieldErrors,
  type Product,
  type ProductGroup,
} from '@/shared/api'
import { formatDateTime, useRequest } from '@/shared/lib'
import { Button, Card, EmptyState, ErrorState, Field, FieldError, LinkButton, Loader, PageHeader } from '@/shared/ui'
import { CharacteristicsField } from './CharacteristicsField'
import { DeliveryMethodsField } from './DeliveryMethodsField'
import { GroupPicker } from './GroupPicker'
import { ProductPhotosField } from './ProductPhotosField'
import { UsdPriceField } from './UsdPriceField'
import {
  EMPTY_PRODUCT_FORM,
  groupCategoryProblem,
  placeServerErrors,
  productToFormValues,
  toProductPayload,
  useDeliveryMethods,
  validateProductForm,
  type ProductFormValues,
} from './productForm'
import { newPhotoFiles, photosFromProduct, saveProductWithPhotos, type PhotoItem } from './productPhotos'
import './ProductEditorPage.css'

const LIST_PATH = '/seller/products'

/** Переход на страницу только что созданного товара */
interface EditorState extends BackState {
  created?: boolean
}

/**
 * Товар в админке витрины: /seller/products/new и /seller/products/:productId — одна и та же форма.
 * Новый товар можно начать с копии другого (?from=<id>, без фото) или сразу в группе (?group=<id>).
 */
export function ProductEditorPage() {
  const { productId } = useParams()
  const [searchParams] = useSearchParams()

  if (productId) return <EditProduct key={productId} productId={Number(productId)} />

  const fromId = Number(searchParams.get('from')) || null
  if (fromId) return <CopyProduct key={fromId} fromId={fromId} />

  const groupId = Number(searchParams.get('group')) || null
  if (groupId) return <NewInGroup key={groupId} groupId={groupId} />

  return <ProductEditor key="new" initial={EMPTY_PRODUCT_FORM} />
}

function EditProduct({ productId }: { productId: number }) {
  const load = useCallback((signal: AbortSignal) => adminApi.getProduct(productId, { signal }), [productId])
  const product = useRequest(load)
  const { mutate } = product
  const handleSaved = useCallback((saved: Product) => mutate(() => saved), [mutate])

  // Ошибка перечитывания после неудачного сохранения форму не убирает: данные уже есть
  if (!product.data && product.status === 'error') {
    const notFound = product.error instanceof ApiError && product.error.status === 404
    return (
      <EditorMessage>
        {notFound ? (
          <EmptyState
            title="Товар не найден"
            text="Возможно, его уже сняли с продажи."
            action={<LinkButton to={LIST_PATH}>К товарам</LinkButton>}
          />
        ) : (
          <ErrorState message={getErrorMessage(product.error)} onRetry={product.reload} />
        )}
      </EditorMessage>
    )
  }
  if (!product.data) {
    return (
      <EditorMessage>
        <Loader />
      </EditorMessage>
    )
  }

  return (
    <ProductEditor
      product={product.data}
      initial={productToFormValues(product.data)}
      onSaved={handleSaved}
      onReload={product.reload}
    />
  )
}

/** Новый товар с полями существующего: так быстрее завести вариант той же модели */
function CopyProduct({ fromId }: { fromId: number }) {
  const load = useCallback((signal: AbortSignal) => adminApi.getProduct(fromId, { signal }), [fromId])
  const source = useRequest(load)

  if (source.status === 'error') {
    return (
      <EditorMessage>
        <ErrorState
          message={`Не удалось открыть товар-образец: ${getErrorMessage(source.error)}`}
          onRetry={source.reload}
          action={<LinkButton to={`${LIST_PATH}/new`}>Начать с чистого листа</LinkButton>}
        />
      </EditorMessage>
    )
  }
  if (!source.data) {
    return (
      <EditorMessage>
        <Loader />
      </EditorMessage>
    )
  }

  return <ProductEditor initial={productToFormValues(source.data)} copyOf={source.data} />
}

/** Новый товар сразу в группе — и в её категории */
function NewInGroup({ groupId }: { groupId: number }) {
  const load = useCallback((signal: AbortSignal) => adminApi.getGroup(groupId, { signal }), [groupId])
  const group = useRequest(load)

  if (group.status === 'error') {
    return (
      <EditorMessage>
        <ErrorState
          message={`Не удалось открыть группу: ${getErrorMessage(group.error)}`}
          onRetry={group.reload}
          action={<LinkButton to={`${LIST_PATH}/new`}>Начать без группы</LinkButton>}
        />
      </EditorMessage>
    )
  }
  if (!group.data) {
    return (
      <EditorMessage>
        <Loader />
      </EditorMessage>
    )
  }

  return (
    <ProductEditor
      initial={{ ...EMPTY_PRODUCT_FORM, groupId, categoryId: group.data.category?.id ?? null }}
      initialGroup={group.data}
    />
  )
}

function EditorMessage({ children }: { children: ReactNode }) {
  return (
    <>
      <BackButton fallback={LIST_PATH} />
      <Card>{children}</Card>
    </>
  )
}

interface ProductEditorProps {
  /** Сохранённый товар; нет — новый */
  product?: Product
  initial: ProductFormValues
  /** Новый товар начат с копии этого */
  copyOf?: Product
  /** Группа из initial.groupId, если уже загружена */
  initialGroup?: ProductGroup
  onSaved?: (product: Product) => void
  /** Перечитать товар: часть шагов сохранения могла пройти */
  onReload?: () => void
}

function ProductEditor({ product, initial, copyOf, initialGroup, onSaved, onReload }: ProductEditorProps) {
  const { shop } = useSeller()
  const navigate = useNavigate()
  const location = useLocation()
  const { cameFromApp, goBack } = useBack(LIST_PATH)
  const methods = useDeliveryMethods()
  const characteristics = useCharacteristics()
  const categories = useCategories()

  const [values, setValues] = useState(initial)
  const [photos, setPhotos] = useState<PhotoItem[]>(() => (product ? photosFromProduct(product) : []))
  const [errors, setErrors] = useState<FieldErrors>({})
  const [saving, setSaving] = useState(false)
  /** Сообщение об успехе в панели сохранения; пропадает при следующей правке */
  const [notice, setNotice] = useState(() =>
    (location.state as EditorState | null)?.created ? 'Товар выставлен на продажу' : undefined,
  )
  /** Растёт после сохранения — таблица товаров группы перечитывается */
  const [savedCount, setSavedCount] = useState(0)

  // Группа с осями: выбранная в поиске известна сразу, у сохранённого товара — догружается
  const [picked, setPicked] = useState<ProductGroup | null>(initialGroup ?? null)
  const loadGroup = useCallback(
    (signal: AbortSignal) =>
      values.groupId === null ? Promise.resolve(null) : adminApi.getGroup(values.groupId, { signal }),
    [values.groupId],
  )
  const groupRequest = useRequest(loadGroup)
  /** null — без группы, undefined — ещё загружается */
  let group: ProductGroup | null | undefined
  if (values.groupId === null) group = null
  else if (groupRequest.data?.id === values.groupId) group = groupRequest.data
  else if (picked?.id === values.groupId) group = picked
  const groupError = group === undefined && groupRequest.status === 'error' ? groupRequest.error : undefined
  const axes = group?.axes ?? []
  const groupMismatch = groupCategoryProblem(group, values.categoryId, categories.data) !== undefined

  function change(next: ProductFormValues) {
    setValues(next)
    setNotice(undefined)
  }

  async function handleSave() {
    const localErrors = validateProductForm(values, {
      shop,
      methods,
      group,
      characteristics: characteristics.data,
      categories: categories.data,
    })
    setErrors(localErrors)
    if (Object.keys(localErrors).length > 0) return

    setSaving(true)
    setNotice(undefined)
    try {
      const payload = toProductPayload(values)
      if (product) {
        const updated = await saveProductWithPhotos(product, payload, photos)
        onSaved?.(updated)
        setValues(productToFormValues(updated))
        setPhotos(photosFromProduct(updated))
        setSavedCount((count) => count + 1)
        setNotice('Сохранено')
      } else {
        const created = await adminApi.createProduct({ ...payload, images: newPhotoFiles(photos) })
        navigate(`${LIST_PATH}/${created.id}`, {
          replace: true,
          state: { created: true, cameFromApp } satisfies EditorState,
        })
      }
    } catch (error) {
      setErrors(placeServerErrors(getFieldErrors(error)))
      // Часть шагов (удаление фото) могла пройти — перечитываем товар, форму не трогаем
      onReload?.()
    } finally {
      setSaving(false)
    }
  }

  // --- Снятие с продажи ---

  const [confirming, setConfirming] = useState(false)
  const [archiving, setArchiving] = useState(false)
  const [archiveError, setArchiveError] = useState<string[]>()

  async function handleArchive() {
    if (!product) return
    setArchiving(true)
    setArchiveError(undefined)
    try {
      await adminApi.archiveProduct(product.id)
      goBack()
    } catch (error) {
      setArchiveError([getErrorMessage(error)])
      setArchiving(false)
    }
  }

  let title = 'Новый товар'
  let subtitle
  if (product) {
    title = product.title
    subtitle = `Артикул ${product.id} · изменён ${formatDateTime(product.updated_at)}`
  } else if (copyOf) {
    title = copyOf.group ? 'Новый вариант' : 'Новый товар'
    subtitle = `На основе «${copyOf.title}» — фото не копируются`
  }

  const hasErrors = Object.keys(errors).length > 0

  return (
    <div className="product-editor">
      <BackButton fallback={LIST_PATH} />
      <PageHeader
        title={title}
        subtitle={subtitle}
        actions={
          product && (
            <>
              <LinkButton
                to={`${LIST_PATH}/new?from=${product.id}`}
                title="Новый товар с полями этого — останется поменять характеристики и фото"
              >
                {product.group ? '+ Вариант' : 'Копировать'}
              </LinkButton>
              <a className="ui-button ui-button--default" href={`/products/${product.id}`} target="_blank" rel="noreferrer">
                На витрине ↗
              </a>
            </>
          )
        }
      />
      <FieldError messages={errors.non_field_errors} />

      <div className="product-editor__layout">
        <div className="product-editor__main">
          <Card title="Основное">
            <div className="ui-form">
              <Field label="Название" errors={errors.title}>
                <input
                  className="ui-input"
                  value={values.title}
                  onChange={(event) => change({ ...values, title: event.target.value })}
                  aria-invalid={Boolean(errors.title)}
                  maxLength={255}
                  autoFocus={!product}
                />
              </Field>
              <Field
                label="Категория"
                errors={errors.category_id}
                hint="Без категории товар есть в общей ленте, но ни в одном разделе каталога."
              >
                <CategorySelect
                  categories={categories}
                  value={values.categoryId}
                  onChange={(categoryId) => change({ ...values, categoryId })}
                  emptyLabel="Без категории"
                  invalid={Boolean(errors.category_id)}
                />
              </Field>
              <Field label="Описание" errors={errors.description}>
                <textarea
                  className="ui-input product-editor__description"
                  value={values.description}
                  onChange={(event) => change({ ...values, description: event.target.value })}
                  aria-invalid={Boolean(errors.description)}
                />
              </Field>
            </div>
          </Card>

          <Card
            title="Фото"
            actions={
              <span className="product-editor__count">
                {photos.length} из {PRODUCT_PHOTOS_MAX}
              </span>
            }
          >
            <ProductPhotosField
              value={photos}
              onChange={(next) => {
                setPhotos(next)
                setNotice(undefined)
              }}
              errors={errors.images}
            />
          </Card>

          <Card title="Варианты и характеристики">
            <div className="product-editor__variants">
              <section aria-labelledby="product-editor-group">
                <h3 id="product-editor-group" className="product-editor__subtitle">
                  Группа вариантов
                </h3>
                <GroupPicker
                  group={group}
                  error={groupError}
                  categoryId={values.categoryId}
                  mismatch={groupMismatch}
                  onRetry={groupRequest.reload}
                  onChange={(next) => {
                    setPicked(next)
                    change({
                      ...values,
                      groupId: next?.id ?? null,
                      // Товар без категории попадает в категорию выбранной группы
                      categoryId: values.categoryId ?? next?.category?.id ?? null,
                    })
                  }}
                />
                <FieldError messages={errors.group} />
              </section>
              <section aria-labelledby="product-editor-characteristics">
                <h3 id="product-editor-characteristics" className="product-editor__subtitle">
                  Характеристики
                </h3>
                <CharacteristicsField
                  rows={values.characteristics}
                  axes={axes}
                  characteristics={characteristics}
                  categoryId={values.categoryId}
                  categories={categories}
                  onChange={(rows) => change({ ...values, characteristics: rows })}
                  errors={errors.characteristics}
                />
              </section>
            </div>
          </Card>

          {group && (
            <Card title="Товары группы" flush>
              <GroupProducts key={`${group.id}-${savedCount}`} group={group} currentId={product?.id} />
            </Card>
          )}
        </div>

        <div className="product-editor__side">
          <Card title="Цена и наличие">
            <div className="ui-form">
              <UsdPriceField
                value={values.priceUsd}
                onChange={(priceUsd) => change({ ...values, priceUsd })}
                errors={errors.price_usd}
              />
              <Field label="В наличии, шт." errors={errors.quantity}>
                <input
                  className="ui-input"
                  type="number"
                  min={0}
                  step={1}
                  value={values.quantity}
                  onChange={(event) => change({ ...values, quantity: event.target.value })}
                  aria-invalid={Boolean(errors.quantity)}
                />
              </Field>
            </div>
          </Card>

          <Card title="Получение">
            <DeliveryMethodsField
              shop={shop}
              methods={methods}
              value={values.deliveryIds}
              onChange={(deliveryIds) => change({ ...values, deliveryIds })}
              errors={errors.delivery_method_ids}
            />
          </Card>

          {product && (
            <Card title="Снятие с продажи">
              <p className="product-editor__hint">Товар пропадёт с витрины. Заказы с ним останутся в истории.</p>
              <FieldError messages={archiveError} />
              {confirming ? (
                <div className="product-editor__confirm">
                  <Button variant="danger" onClick={handleArchive} disabled={archiving}>
                    {archiving ? 'Снимаем…' : 'Да, снять'}
                  </Button>
                  <Button variant="text" onClick={() => setConfirming(false)} disabled={archiving}>
                    Отмена
                  </Button>
                </div>
              ) : (
                <Button onClick={() => setConfirming(true)}>Снять с продажи</Button>
              )}
            </Card>
          )}
        </div>
      </div>

      {/* Панель сохранения всегда под рукой, сколько ни листай форму */}
      <div className="product-editor__bar">
        <span
          className={hasErrors ? 'product-editor__status product-editor__status--error' : 'product-editor__status'}
          role="status"
        >
          {hasErrors ? 'Не сохранено — проверьте отмеченные поля' : notice}
        </span>
        <Button variant="text" onClick={goBack} disabled={saving}>
          {product ? 'Закрыть' : 'Отмена'}
        </Button>
        <Button variant="primary" onClick={handleSave} disabled={saving || group === undefined}>
          {saving ? 'Сохраняем…' : product ? 'Сохранить' : 'Выставить на продажу'}
        </Button>
      </div>
    </div>
  )
}
