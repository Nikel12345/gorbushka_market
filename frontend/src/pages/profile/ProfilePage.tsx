import { useAuth } from '@/features/auth'

export function ProfilePage() {
  const { user } = useAuth()
  if (!user) return null

  return (
    <section>
      <h1>Профиль</h1>
      <dl>
        <dt>Email</dt>
        <dd>{user.email}</dd>
        <dt>Имя</dt>
        <dd>{[user.first_name, user.last_name].filter(Boolean).join(' ') || '—'}</dd>
        <dt>Дата регистрации</dt>
        <dd>{new Date(user.date_joined).toLocaleDateString('ru-RU')}</dd>
      </dl>
    </section>
  )
}
