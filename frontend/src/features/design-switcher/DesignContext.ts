import { createContext, useContext } from 'react'
import { DEFAULT_DESIGN, type DesignId } from './designs'

/** Текущий вариант дизайна для страниц витрины. Значение даёт каркас витрины (AppLayout). */
export const DesignContext = createContext<DesignId>(DEFAULT_DESIGN)

export function useCurrentDesign(): DesignId {
  return useContext(DesignContext)
}
