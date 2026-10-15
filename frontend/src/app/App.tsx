import { RouterProvider } from 'react-router'
import { AuthProvider } from '@/features/auth'
import { CartProvider } from '@/features/cart'
import { router } from './router'

// Корневой компонент: глобальные провайдеры и роутер.
export function App() {
  return (
    <AuthProvider>
      {/* Корзина общая для шапки, ленты и страницы товара; зависит от того, кто вошёл */}
      <CartProvider>
        <RouterProvider router={router} />
      </CartProvider>
    </AuthProvider>
  )
}
