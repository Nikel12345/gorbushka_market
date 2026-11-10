import type { ShowcaseDesignId } from '@/features/design-switcher'
import { useCategories } from './hooks'
import { catalogLink } from './links'

/** Пункт полосы категорий: подпись как в макете, категория — по slug (id берётся из API) */
interface NavItemDef {
  label: string
  slug?: string
  /** Первый пункт — малиновым */
  accent?: boolean
}

const NEW: NavItemDef = { label: 'Новинки', accent: true }

/** Полоса под шапкой на компьютере */
const DESKTOP: Record<ShowcaseDesignId, NavItemDef[]> = {
  vitrina: [
    NEW,
    { label: 'Смартфоны', slug: 'smartfony' },
    { label: 'Ноутбуки', slug: 'noutbuki' },
    { label: 'Наушники и колонки', slug: 'audiotekhnika' },
    { label: 'Игры и консоли', slug: 'igry-i-konsoli' },
    { label: 'Телевизоры и проекторы', slug: 'tv-i-multimedia' },
    { label: 'Фото и видео', slug: 'foto-i-video' },
    { label: 'Умный дом', slug: 'umnyy-dom' },
    { label: 'Комплектующие ПК', slug: 'komplektuyushchie-dlya-pk' },
    { label: 'Аксессуары', slug: 'aksessuary-dlya-smartfonov' },
  ],
  night: [
    NEW,
    { label: 'Смартфоны', slug: 'smartfony' },
    { label: 'Ноутбуки', slug: 'noutbuki' },
    { label: 'Наушники и колонки', slug: 'audiotekhnika' },
    { label: 'Игры и консоли', slug: 'igry-i-konsoli' },
    { label: 'Телевизоры', slug: 'televizory' },
    { label: 'Фото и видео', slug: 'foto-i-video' },
    { label: 'Умный дом', slug: 'umnyy-dom' },
    { label: 'Комплектующие ПК', slug: 'komplektuyushchie-dlya-pk' },
  ],
  afisha: [
    { label: 'Смартфоны', slug: 'smartfony' },
    { label: 'Ноутбуки', slug: 'noutbuki' },
    { label: 'Аудио', slug: 'audiotekhnika' },
    { label: 'Консоли', slug: 'igrovye-konsoli' },
    { label: 'ТВ', slug: 'tv-i-multimedia' },
    { label: 'Фото', slug: 'foto-i-video' },
    { label: 'Умный дом', slug: 'umnyy-dom' },
    { label: 'Комплектующие ПК', slug: 'komplektuyushchie-dlya-pk' },
  ],
}

/** Ряд чипсов под поиском на телефоне */
const MOBILE: Record<ShowcaseDesignId, NavItemDef[]> = {
  vitrina: [
    NEW,
    { label: 'Смартфоны', slug: 'smartfony' },
    { label: 'Ноутбуки', slug: 'noutbuki' },
    { label: 'Наушники', slug: 'naushniki' },
    { label: 'Консоли', slug: 'igrovye-konsoli' },
  ],
  night: [],
  afisha: [
    NEW,
    { label: 'Смартфоны', slug: 'smartfony' },
    { label: 'Ноутбуки', slug: 'noutbuki' },
    { label: 'Аудио', slug: 'audiotekhnika' },
    { label: 'Консоли', slug: 'igrovye-konsoli' },
    { label: 'ТВ', slug: 'tv-i-multimedia' },
  ],
}

export interface NavItem {
  label: string
  to: string
  categoryId: number | null
  accent: boolean
}

/** Пункты полосы категорий с готовыми ссылками. Категории без slug в каталоге не показываются. */
export function useNavItems(design: ShowcaseDesignId, place: 'desktop' | 'mobile'): NavItem[] {
  const categories = useCategories()
  const defs = (place === 'desktop' ? DESKTOP : MOBILE)[design]
  const items: NavItem[] = []
  for (const def of defs) {
    if (!def.slug) {
      items.push({ label: def.label, to: '/', categoryId: null, accent: Boolean(def.accent) })
      continue
    }
    const category = categories.find((item) => item.slug === def.slug)
    if (category) items.push({ label: def.label, to: catalogLink(undefined, category.id), categoryId: category.id, accent: false })
  }
  return items
}
