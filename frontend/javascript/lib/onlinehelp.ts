const onlinehelpLink = (el: HTMLElement, emit: (event: string, ...args: any[]) => void) => {
  // debug helper, uncomment: el.style.outline = '2px dotted red'
  el.addEventListener('click', (evt) => {
    emit('onlinehelp-click', el.dataset.onlinehelpHref)
    evt.preventDefault()
  })
}

export const registerOnlinehelpLinks = (node: HTMLElement, emit?: (event: string, ...args: any[]) => void) => {
  node.querySelectorAll<HTMLElement>('[data-onlinehelp-href]')
    .forEach((el) => onlinehelpLink(el, emit!))
}