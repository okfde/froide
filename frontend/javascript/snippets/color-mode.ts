const storageKey = 'colortheme'
const storedTheme = localStorage.getItem(storageKey)

const DEFAULT_THEME = 'light'

const getPreferredTheme = (): string => {
  if (storedTheme !== null) {
    return storedTheme
  }

  return DEFAULT_THEME
}

const getCurrentTheme = (): string | null => {
  return document.documentElement.getAttribute('data-bs-theme')
}

const toggle = document.getElementById('darkmode-toggle')

const setTheme = (theme: string): void => {
  document.documentElement.setAttribute('data-bs-theme', theme)

  const icon = toggle?.querySelector('i')
  if (theme === 'dark') {
    icon?.classList.replace('fa-moon-o', 'fa-sun-o')
  } else {
    icon?.classList.replace('fa-sun-o', 'fa-moon-o')
  }

  localStorage.setItem(storageKey, theme)
}

if (getCurrentTheme() === DEFAULT_THEME) setTheme(getPreferredTheme())

window.addEventListener('DOMContentLoaded', () => {
  toggle?.addEventListener('click', () => {
    const currentTheme = getCurrentTheme()
    if (currentTheme === 'dark') {
      setTheme('light')
    } else {
      setTheme('dark')
    }
  })
})
