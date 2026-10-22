import { useBack } from './useBack'
import './catalogAdmin.css'

export function BackButton({ fallback }: { fallback: string }) {
  const { goBack } = useBack(fallback)
  return (
    <button type="button" className="seller-back" onClick={goBack}>
      ← Назад
    </button>
  )
}
