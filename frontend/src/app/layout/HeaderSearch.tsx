import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router'
import { updateSearchParams } from '@/shared/lib'
import { SearchIcon } from './MarketNavIcons'

/**
 * Поиск в шапке. Ищет по ленте на главной через ?q= — тот же параметр, что у панели фильтров,
 * поэтому на главной остальные фильтры сохраняются, а с других страниц поиск ведёт на главную.
 */
export function HeaderSearch() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const onHome = pathname === '/'
  const urlQuery = onHome ? (searchParams.get('q') ?? '') : ''

  // Поле повторяет ?q= при навигации (назад, сброс фильтров), но между ними редактируется свободно
  const [value, setValue] = useState(urlQuery)
  const [syncedQuery, setSyncedQuery] = useState(urlQuery)
  if (urlQuery !== syncedQuery) {
    setSyncedQuery(urlQuery)
    setValue(urlQuery)
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const q = value.trim()
    const base = onHome ? searchParams : new URLSearchParams()
    const search = updateSearchParams(base, { q, page: null }).toString()
    navigate({ pathname: '/', search: search ? `?${search}` : '' })
  }

  return (
    <form className="market-search" role="search" onSubmit={handleSubmit}>
      <input
        className="market-search__input"
        type="search"
        placeholder="Найти товары"
        aria-label="Поиск товаров"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        maxLength={200}
      />
      <button type="submit" className="market-search__button" aria-label="Найти">
        <SearchIcon />
      </button>
    </form>
  )
}
