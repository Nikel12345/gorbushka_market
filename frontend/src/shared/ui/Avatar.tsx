// Цвет аватара стабилен для одного и того же имени
const COLORS = ['#e57373', '#f06292', '#ba68c8', '#7986cb', '#4fc3f7', '#4db6ac', '#81c784', '#ffb74d', '#a1887f', '#90a4ae']

function pickColor(name: string): string {
  let hash = 0
  for (const char of name) hash = (hash * 31 + char.charCodeAt(0)) | 0
  return COLORS[Math.abs(hash) % COLORS.length]
}

/** Круглый аватар с первой буквой имени. */
export function Avatar({ name, size = 32 }: { name: string; size?: number }) {
  const letter = name.trim().charAt(0).toUpperCase() || '?'
  return (
    <span
      className="ui-avatar"
      aria-hidden="true"
      style={{ width: size, height: size, fontSize: Math.round(size * 0.45), background: pickColor(name) }}
    >
      {letter}
    </span>
  )
}
