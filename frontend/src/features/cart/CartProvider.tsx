import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useAuth } from '@/features/auth'
import { cartApi, type Cart } from '@/shared/api'
import { CartContext, type CartContextValue, type CartStatus } from './CartContext'

// Ключ «товара» для очистки всей корзины в списке идущих запросов (id товаров начинаются с 1)
const CLEAR_KEY = 0

/**
 * Корзина текущего пользователя или гостя — одна на приложение: значок в шапке, кнопки в ленте
 * и на странице товара видят одно и то же. Любое изменение возвращает корзину целиком,
 * её и показываем — без ручного пересчёта на клиенте.
 * Гостевая корзина живёт в сессии на сервере; при входе сервер переносит её в корзину аккаунта.
 */
export function CartProvider({ children }: { children: ReactNode }) {
  const { user, status: authStatus } = useAuth()
  // Чья корзина: id пользователя, null — гость, undefined — ещё не знаем (сессия проверяется)
  const owner = authStatus === 'loading' ? undefined : (user?.id ?? null)

  const [cart, setCart] = useState<Cart | null>(null)
  const [loadStatus, setLoadStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [pending, setPending] = useState<ReadonlySet<number>>(new Set())
  // Номер «поколения» данных: ответ на старый запрос не затирает более свежую корзину
  const versionRef = useRef(0)

  const refresh = useCallback(() => {
    const version = ++versionRef.current
    cartApi.get().then(
      (next) => {
        if (version !== versionRef.current) return
        setCart(next)
        setLoadStatus('ready')
      },
      () => {
        if (version === versionRef.current) setLoadStatus('error')
      },
    )
  }, [])

  // Вошёл (корзина гостя уже перенесена в аккаунт), вышел или вошёл другой — перечитываем
  const [loadedFor, setLoadedFor] = useState<number | null | undefined>(undefined)
  if (owner !== loadedFor) {
    setLoadedFor(owner)
    setCart(null)
    setLoadStatus('loading')
  }

  useEffect(() => {
    if (owner === undefined) {
      versionRef.current++
      return
    }
    refresh()
  }, [owner, refresh])

  const run = useCallback(
    async (productId: number, request: () => Promise<Cart>) => {
      const version = ++versionRef.current
      setPending((prev) => new Set(prev).add(productId))
      try {
        const next = await request()
        if (version === versionRef.current) {
          setCart(next)
          setLoadStatus('ready')
        }
      } catch (error) {
        // Корзина могла измениться в другой вкладке — подтягиваем актуальную
        refresh()
        throw error
      } finally {
        setPending((prev) => {
          const rest = new Set(prev)
          rest.delete(productId)
          return rest
        })
      }
    },
    [refresh],
  )

  const quantities = useMemo(
    () => new Map(cart?.items.map((line) => [line.product.id, line.quantity]) ?? []),
    [cart],
  )

  const value = useMemo<CartContextValue>(() => {
    const status: CartStatus = authStatus === 'loading' ? 'loading' : loadStatus

    return {
      status,
      cart,
      itemsCount: cart?.items_count ?? 0,
      quantityOf: (productId) => quantities.get(productId) ?? 0,
      isPending: (productId) => pending.has(productId) || pending.has(CLEAR_KEY),
      add: (productId) => run(productId, () => cartApi.add(productId)),
      setQuantity: (productId, quantity) => run(productId, () => cartApi.setQuantity(productId, quantity)),
      remove: (productId) => run(productId, () => cartApi.remove(productId)),
      clear: () => run(CLEAR_KEY, cartApi.clear),
      refresh,
    }
  }, [authStatus, loadStatus, cart, quantities, pending, run, refresh])

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}
