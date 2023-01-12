const setTheme = (theme: string): void => {
  if (
    theme === 'auto' &&
    window.matchMedia('(prefers-color-scheme: dark)').matches
  ) {
    document.documentElement.setAttribute('data-bs-theme', 'dark')
  } else {
    document.documentElement.setAttribute('data-bs-theme', theme)
  }
}

const getCurrentTheme = (): string | null => {
  return document.documentElement.getAttribute('data-bs-theme')
}

window.addEventListener('DOMContentLoaded', () => {
  const defaultTheme = getCurrentTheme()
  if (defaultTheme === null) {
    return
  }

  const toggle = document.getElementById('darkmode-toggle')
  if (toggle === null) {
    return
  }

  toggle.addEventListener('click', () => {
    const currentTheme = getCurrentTheme()
    if (currentTheme === null) {
      return
    }
    const icon = toggle.querySelector('i')
    if (icon === null) {
      return
    }
    if (currentTheme === 'dark') {
      icon.classList.replace('fa-sun-o', 'fa-moon-o')
      setTheme('light')
    } else {
      icon.classList.replace('fa-moon-o', 'fa-sun-o')
      setTheme('dark')
    }
  })
})
