const onlinehelpLink = (el: HTMLElement, emit: (event: string, ...args: any[]) => void) => {
  // debug helper, uncomment: el.style.outline = '2px dotted red'
  el.addEventListener('click', (evt) => {
    const href = el.dataset.onlinehelpHref || (el.target && el.href)
    if (!href) {
      console.warn('online help click, but no href found')
      return
    }
    emit('onlinehelp-click', href)
    evt.preventDefault()
  })
}

export const registerOnlinehelpLinks = (node: HTMLElement, emit?: (event: string, ...args: any[]) => void) => {
  node.querySelectorAll<HTMLElement>('[data-onlinehelp-href], [target="onlinehelp"]')
    .forEach((el) => onlinehelpLink(el, emit!))
}