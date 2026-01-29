import { Tooltip } from 'bootstrap'

const collapsePersistent = (el: HTMLElement) => {
  const id = el.id
  const key = 'froide-collapsible-' + id
  try {
    const { collapsed } = JSON.parse(localStorage.getItem(key))
    // we don't use the .hide/.show methods to not trigger animation
    el.classList.toggle('show', !collapsed)
    const controllerEl = document.querySelector(`[data-bs-target="#${id}"]`)
    controllerEl?.classList.toggle('collapsed', collapsed)
    controllerEl?.setAttribute('aria-expanded', collapsed ? 'false' : 'true')
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

// registerBs called onDomReady in bootstrap.ts, but also for each DjangoSlot[has-bs-directives].
// In practice, this just works out and they don't interfere.
// In theory, onDomReady might attach unnecessary/problematic listeners to something like
// <FooVueComponent><template #barSlot><div data-bs-collapse-persistent>
// Should this cause problems, we could make sure that the queried Elements
// are not descendants of <template>.
const registerBs = (node: HTMLElement) => {
  node
    .querySelectorAll<HTMLElement>('[data-bs-toggle="tooltip"]')
    .forEach((el) => new Tooltip(el))
  node
    .querySelectorAll<HTMLElement>('[data-bs-collapse-persistent]')
    .forEach((el) => collapsePersistent(el))
}

export { registerBs }
