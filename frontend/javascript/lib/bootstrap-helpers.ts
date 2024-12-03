const collapsePersistent = (el: HTMLElement) => {
  const id = el.id
  const key = 'froide-collapsible-' + id
  try {
    const { collapsed } = JSON.parse(localStorage.getItem(key))
    // we don't use the .hide/.show methods to not trigger animation
    el.classList.toggle('show', !collapsed)
    const controllerEl = document.querySelector(`[data-bs-target="#${id}"]`)
    controllerEl?.classList.toggle('collapsed', collapsed)
    controllerEl?.setAttribute('aria-expanded', !collapsed)
  } catch {
    // noop
  }
  el.addEventListener('hide.bs.collapse', () => {
    localStorage.setItem(key, JSON.stringify({ collapsed: true }))
  })
  el.addEventListener('show.bs.collapse', () => {
    localStorage.setItem(key, JSON.stringify({ collapsed: false }))
  })
}

export {
  collapsePersistent
}
