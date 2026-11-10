import type { ShowcaseDesignId } from '@/features/design-switcher'
import { AfishaIntro, AfishaStore } from './Afisha'
import { NightIntro } from './Night'
import { VitrinaIntro, VitrinaStore } from './Vitrina'
import './Storefront.css'
import './Showcase.css'

/** Блоки главной над лентой — свои у каждого «витринного» варианта */
export function StorefrontIntro({ design }: { design: ShowcaseDesignId }) {
  switch (design) {
    case 'vitrina':
      return <VitrinaIntro />
    case 'night':
      return <NightIntro />
    case 'afisha':
      return <AfishaIntro />
  }
}

/** Блоки главной под лентой (о магазине); у «Ночи» их нет */
export function StorefrontOutro({ design }: { design: ShowcaseDesignId }) {
  switch (design) {
    case 'vitrina':
      return <VitrinaStore />
    case 'afisha':
      return <AfishaStore />
    case 'night':
      return null
  }
}
