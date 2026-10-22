import { createBrowserRouter, Navigate } from 'react-router'
import { GuestOnly, RequireAuth, RequireStaff } from '@/features/auth'
import { AboutPage } from '@/pages/about'
import { CartPage } from '@/pages/cart'
import { CheckoutPage } from '@/pages/checkout'
import { HomePage } from '@/pages/home'
import { LoginPage } from '@/pages/login'
import { OrderDetailsPage, OrdersPage } from '@/pages/orders'
import { ProductPage } from '@/pages/product'
import { ProfilePage } from '@/pages/profile'
import { RegisterPage } from '@/pages/register'
import { CategoriesPage } from '@/pages/seller-categories'
import { CharacteristicsPage } from '@/pages/seller-characteristics'
import { GroupPage, GroupsPage } from '@/pages/seller-groups'
import { SellerOrdersPage } from '@/pages/seller-orders'
import { ProductEditorPage } from '@/pages/seller-product-editor'
import { SellerProductsPage } from '@/pages/seller-products'
import { SellerProfilePage } from '@/pages/seller-profile'
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
      { path: 'about', element: <AboutPage /> },
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
  // Админка магазина (только is_staff) — со своим каркасом (панель + меню справа), без шапки витрины.
  // Витрина (товары, категории, характеристики, группы вариантов) — то, что ведёт менеджер; дальше заказы и профиль.
  // Магазин один, поэтому его id в адресах нет.
  {
    path: 'seller',
    element: (
      <RequireStaff>
        <SellerLayout />
      </RequireStaff>
    ),
    children: [
      { index: true, element: <Navigate to="products" replace /> },
      { path: 'products', element: <SellerProductsPage /> },
      // Добавление и карточка — одна страница-форма
      { path: 'products/new', element: <ProductEditorPage /> },
      { path: 'products/:productId', element: <ProductEditorPage /> },
      { path: 'categories', element: <CategoriesPage /> },
      { path: 'characteristics', element: <CharacteristicsPage /> },
      { path: 'groups', element: <GroupsPage /> },
      { path: 'groups/:groupId', element: <GroupPage /> },
      { path: 'orders', element: <SellerOrdersPage /> },
      { path: 'shop', element: <ShopProfilePage /> },
      { path: 'profile', element: <SellerProfilePage /> },
    ],
  },
])
