import type { ReactNode } from 'react'

interface SidebarLayoutProps {
  /** Левая колонка (фильтры). Прилипает под шапкой — высоту шапки задаёт каркас через --sticky-header-height */
  aside: ReactNode
  children: ReactNode
  /** Ширина левой колонки задаётся через --sidebar-layout-aside */
  className?: string
}

/** Две колонки: узкая слева, контент справа. На узком экране — одна под другой. */
export function SidebarLayout({ aside, children, className }: SidebarLayoutProps) {
  return (
    <div className={className ? `ui-sidebar-layout ${className}` : 'ui-sidebar-layout'}>
      <div className="ui-sidebar-layout__aside">{aside}</div>
      <div className="ui-sidebar-layout__main">{children}</div>
    </div>
  )
}
