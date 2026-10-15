/** Блок «идёт загрузка» на месте контента. */
export function Loader({ label = 'Загрузка…' }: { label?: string }) {
  return (
    <div className="ui-loader" role="status">
      <span className="ui-spinner" aria-hidden="true" />
      {label}
    </div>
  )
}

/** Тонкая полоса прогресса поверх уже показанного контента (обновление данных). */
export function LinearProgress() {
  return <div className="ui-progress" role="progressbar" aria-label="Обновление" />
}
