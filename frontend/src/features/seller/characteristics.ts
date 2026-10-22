// Справочник характеристик в админке витрины: загрузка и локальные правки после создания и изменения
import { adminApi, type Characteristic, type CharacteristicValue } from '@/shared/api'
import { useRequest } from '@/shared/lib'

const loadCharacteristics = (signal: AbortSignal) => adminApi.listCharacteristics({ signal })

/** Все характеристики со значениями. Новые добавляются через mutate — без перезапроса. */
export function useCharacteristics() {
  return useRequest(loadCharacteristics)
}

export type CharacteristicsRequest = ReturnType<typeof useCharacteristics>

/** Порядок как на бэке: sort_order, затем id */
function byOrder<T extends { id: number; sort_order: number }>(a: T, b: T) {
  return a.sort_order - b.sort_order || a.id - b.id
}

export function withCharacteristic(list: Characteristic[], created: Characteristic): Characteristic[] {
  return [...list, created].sort(byOrder)
}

/** После правки: название, категория и порядок могли смениться */
export function withUpdatedCharacteristic(list: Characteristic[], updated: Characteristic): Characteristic[] {
  return list.map((item) => (item.id === updated.id ? updated : item)).sort(byOrder)
}

export function withValue(list: Characteristic[], characteristicId: number, value: CharacteristicValue): Characteristic[] {
  return list.map((item) =>
    item.id === characteristicId ? { ...item, values: [...item.values, value].sort(byOrder) } : item,
  )
}
