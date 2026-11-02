/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  /** 'off' — скрыть панель выбора дизайна (shared/config) */
  readonly VITE_DESIGN_SWITCHER?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
