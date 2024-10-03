function scrollToAnchor(
  id: string,
  options: boolean | Record<string, unknown> | undefined = true
): void {
  window.setTimeout(() => {
    const el = document.getElementById(id)
    if (el == null) {
      return
    }
    if (el.classList.contains('collapse') && !el.classList.contains('show')) {
      // skip if this container collapses
      return
    }
    el.scrollIntoView(options)
  }, 200)
}

const scrollNavIntoViewIfNecessary = (): void => {
  const header = document.querySelector('main nav') as HTMLElement
  if (header === null) return
  const rect = header.getBoundingClientRect()
  if (rect.bottom < 0) {
    // timeout to make it feel less jarring
    setTimeout(() => header.scrollIntoView({ behavior: 'smooth' }), 500)
  }
}

const getHeight = (el: HTMLElement): number => {
  const style = window.getComputedStyle(el)
  const display = style.display
  const maxHeight = style.maxHeight?.replace('px', '').replace('%', '')
  let wantedHeight = 0

  // if its not hidden we just return normal height
  if (display !== 'none' && maxHeight !== '0') {
    return el.offsetHeight
  }

  // the element or one of its parents is hidden so:

  // making the el and all hidden parents block so we can meassure its height but still be hidden
  const elemState: string[] = []
  let cur: HTMLElement | null = el
  while (cur !== null && cur.offsetHeight === 0) {
    elemState.push(cur.style.cssText)
    cur.style.setProperty('visibility', 'hidden', 'important')
    cur.style.setProperty('display', 'block', 'important')
    cur = cur.parentElement
  }
  wantedHeight = el.offsetHeight

  // reverting to the original values
  cur = el
  while (cur !== null && elemState.length > 0) {
    cur.style.cssText = elemState[0]
    elemState.shift()
    cur = cur.parentElement
  }

  return wantedHeight
}

/**
 * toggleSlide mimics the jQuery version of slideDown and slideUp
 * all in one function comparing the max-heigth to 0
 */
const toggleSlide = (el: HTMLElement, seconds = 0.3): void => {
  let elMaxHeight = '0px'

  const dataMaxHeight = el.getAttribute('data-max-height')
  if (dataMaxHeight !== null) {
    // we've already used this before, so everything is setup
    let maxHeight = el.style.maxHeight
    maxHeight = maxHeight?.replace('px', '').replace('%', '')
    if (maxHeight === '0') {
      el.style.maxHeight = dataMaxHeight
    } else {
      el.style.maxHeight = '0'
    }
  } else {
    elMaxHeight = `${getHeight(el)}px`

    el.style.transition = `max-height ${seconds}s ease-in-out`
    el.style.overflow = 'hidden'
    el.style.maxHeight = '0'
    el.setAttribute('data-max-height', elMaxHeight)
    el.style.display = 'block'

    // we use requestAnimationFrame to modify maxHeight after the display and transition are set
    requestAnimationFrame(() => {
      el.style.maxHeight = elMaxHeight
    })
  }
}

const slideUp = (el: HTMLElement, seconds = 0.3): void => {
  const elMaxHeight = `${getHeight(el)}px`
  el.style.maxHeight = elMaxHeight
  el.setAttribute('data-max-height', elMaxHeight)

  el.style.transition = `max-height ${seconds}s ease-in-out`
  el.style.overflow = 'hidden'

  requestAnimationFrame(() => {
    el.style.maxHeight = '0'
  })
}

const addText = (dataset: DOMStringMap): void => {
  if (!dataset.addtextfield) {
    return
  }
  const textField = document.querySelector(
    dataset.addtextfield
  ) as HTMLInputElement
  if (textField === null) {
    return
  }
  let text = textField.value
  const addedText = dataset.addtext
  if (!addedText) {
    return
  }
  if (text.includes(addedText)) {
    return
  }
  if (text.includes('\n...\n')) {
    text = text.replace('...', addedText)
  } else {
    const textParts = text.split('\n\n')
    text = [textParts[0], addedText, textParts[textParts.length - 1]].join(
      '\n\n'
    )
  }
  textField.value = text
}

const beforeunloadHandler = (e: BeforeUnloadEvent) => e.preventDefault()
let isBeforeunloadGuarded = false
const guardBeforeunload = (enable: boolean): void => {
  if (enable) {
    if (!isBeforeunloadGuarded) {
      window.addEventListener('beforeunload', beforeunloadHandler)
      isBeforeunloadGuarded = true
    }
  } else {
    window.removeEventListener('beforeunload', beforeunloadHandler)
  }
}

export { addText, scrollToAnchor, scrollNavIntoViewIfNecessary, slideUp, toggleSlide, guardBeforeunload }
