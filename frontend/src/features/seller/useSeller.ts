import { useContext } from 'react'
import { SellerContext } from './SellerContext'

export function useSeller() {
  const context = useContext(SellerContext)
  if (!context) {
    throw new Error('useSeller must be used within SellerContext (SellerLayout)')
  }
  return context
}
