const storageKey = 'colortheme'
const storedTheme = localStorage.getItem(storageKey)

const getPreferredTheme = (): string => {
  if (storedTheme !== null) {
    return storedTheme
  }

  return 'light'
}

const getCurrentTheme = (): string | null => {
  return document.documentElement.getAttribute('data-bs-theme')
}

const toggle = document.getElementById('darkmode-toggle')

const setTheme = (theme: string): void => {
  document.documentElement.setAttribute('data-bs-theme', theme)

  if (toggle === null) {
    return
  }
  const icon = toggle.querySelector('i')
  if (icon === null) {
    return
  }
  if (theme === 'dark') {
    icon.classList.replace('fa-moon-o', 'fa-sun-o')
  } else {
    icon.classList.replace('fa-sun-o', 'fa-moon-o')
  }
  localStorage.setItem(storageKey, theme)
}

setTheme(getPreferredTheme())

window.addEventListener('DOMContentLoaded', () => {
  const defaultTheme = getCurrentTheme()
  if (defaultTheme === null) {
    return
  }

  if (toggle === null) {
    return
  }
  toggle.addEventListener('click', () => {
    const currentTheme = getCurrentTheme()
    if (currentTheme === null) {
      return
    }
    if (currentTheme === 'dark') {
      setTheme('light')
    } else {
      setTheme('dark')
    }
  })
})
