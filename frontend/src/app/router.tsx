import { createBrowserRouter, Navigate } from 'react-router'
import { GuestOnly, RequireAuth } from '@/features/auth'
import { ShopRoute } from '@/features/seller'
import { CartPage } from '@/pages/cart'
import { CheckoutPage } from '@/pages/checkout'
import { HomePage } from '@/pages/home'
import { LoginPage } from '@/pages/login'
import { OrderDetailsPage, OrdersPage } from '@/pages/orders'
import { ProductPage } from '@/pages/product'
import { ProfilePage } from '@/pages/profile'
import { RegisterPage } from '@/pages/register'
import { SellerHomePage } from '@/pages/seller-home'
import { ShopPage } from '@/pages/shop'
import { SellerOrdersPage } from '@/pages/seller-orders'
import { ProductCreateDialog, ProductDialog, SellerProductsPage } from '@/pages/seller-products'
import { SellerProfilePage } from '@/pages/seller-profile'
import { ShopCreatePage } from '@/pages/seller-shop-new'
import { ShopProfilePage } from '@/pages/seller-shop-profile'
import { AppLayout } from './layout/AppLayout'
import { SellerLayout } from './layout/SellerLayout'

export const router = createBrowserRouter([
  // Витрина: шапка с поиском и разделами покупателя на всех страницах
  {
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'products/:productId', element: <ProductPage /> },
      { path: 'shops/:shopId', element: <ShopPage /> },
      {
        path: 'login',
        element: (
          <GuestOnly>
            <LoginPage />
          </GuestOnly>
        ),
      },
      {
        path: 'register',
        element: (
          <GuestOnly>
            <RegisterPage />
          </GuestOnly>
        ),
      },
      {
        path: 'profile',
        element: (
          <RequireAuth>
            <ProfilePage />
          </RequireAuth>
        ),
      },
      {
        path: 'cart',
        element: (
          <RequireAuth>
            <CartPage />
          </RequireAuth>
        ),
      },
      {
        path: 'checkout',
        element: (
          <RequireAuth>
            <CheckoutPage />
          </RequireAuth>
        ),
      },
      {
        path: 'orders',
        element: (
          <RequireAuth>
            <OrdersPage />
          </RequireAuth>
        ),
      },
      {
        path: 'orders/:purchaseId',
        element: (
          <RequireAuth>
            <OrderDetailsPage />
          </RequireAuth>
        ),
      },
    ],
  },
  // Кабинет продавца — со своим каркасом (панель + меню справа), без шапки витрины
  {
    path: 'seller',
    element: (
      <RequireAuth>
        <SellerLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <SellerHomePage /> },
      { path: 'profile', element: <SellerProfilePage /> },
      // Заказы — общий раздел, магазин выбирается на странице
      { path: 'orders', element: <SellerOrdersPage /> },
      { path: 'shops/new', element: <ShopCreatePage /> },
      {
        path: 'shops/:shopId',
        element: <ShopRoute />,
        children: [
          { index: true, element: <Navigate to="products" replace /> },
          {
            path: 'products',
            element: <SellerProductsPage />,
            // Диалоги поверх списка: у каждого свой URL, список под ними не перезагружается
            children: [
              { path: 'new', element: <ProductCreateDialog /> },
              { path: ':productId', element: <ProductDialog /> },
            ],
          },
          { path: 'profile', element: <ShopProfilePage /> },
        ],
      },
    ],
  },
])
