interface StorageItem {
  isExpanded: boolean
}

export default class Message {
  id: string
  element: HTMLElement
  metaContainer: HTMLElement
  expandedClassName = 'alpha-message--expanded'
  metaExpandedClassName = 'alpha-message__meta-container--visible'

  constructor(element: HTMLElement, forceExpand: boolean, isLastItem: boolean) {
    this.id = element.id || ''
    this.element = element
    this.metaContainer = this.element.querySelector(
      '.alpha-message__meta-container'
    ) as HTMLElement

    // event listeners

    // header row
    element
      .querySelector('.alpha-message__head')
      ?.addEventListener('click', this.onHeadClick.bind(this))
    element
      .querySelector('.alpha-message__meta-toggle')
      ?.addEventListener('click', this.toggleMetaContainer.bind(this))
    element
      .querySelectorAll('.alpha-attachment__more-trigger')
      .forEach((el) => {
        el.addEventListener('click', this.showAllAttachments.bind(this))
      })

    // create storage item and/or expand message
    if (!this.storageItem) {
      // create localStorage item
      try {
        // localStorage access may cause DOMException if blocked
        localStorage.setItem(
          this.id,
          JSON.stringify({ isExpanded: isLastItem || forceExpand })
        )
      } catch {
        console.warn('Could not create localStorage item')
      }
      // maybe expand
      if (isLastItem || forceExpand) this.expandMessage()
    } else {
      // expand message according to storage state
      if (this.isExpanded || forceExpand) this.expandMessage()
    }
  }

  get storageItem(): StorageItem | null {
    try {
      // localStorage access may cause DOMException if blocked
      const item = localStorage.getItem(this.id)
      return item ? JSON.parse(item) : null
    } catch {
      return null
    }
  }

  get isExpanded(): boolean {
    const storageItem = this.storageItem
    return storageItem ? storageItem.isExpanded : false
  }

  get isCollapsed(): boolean {
    const storageItem = this.storageItem
    return storageItem ? storageItem.isExpanded === false : false
  }

  updateStorageItem(data: StorageItem): void {
    const storageItem = {
      ...this.storageItem,
      ...data
    }

    try {
      // localStorage access may cause DOMException if blocked
      localStorage.setItem(this.id, JSON.stringify(storageItem))
    } catch {
      console.warn('Could not update localStorage item')
    }
  }

  onHeadClick(e: Event): void {
    this.toggleMessage()
    e.preventDefault()
  }

  toggleMessage(): void {
    if (this.isExpanded) {
      this.collapseMessage()
    } else {
      this.expandMessage()
      if (history.replaceState) {
        history.replaceState(null, '', '#' + this.id)
      }
    }
  }

  expandMessage(): void {
    this.updateStorageItem({ isExpanded: true })
    this.element.classList.add(this.expandedClassName)
  }

  collapseMessage(): void {
    this.updateStorageItem({ isExpanded: false })
    this.element.classList.remove(this.expandedClassName)
    this.metaContainer.classList.remove(this.metaExpandedClassName)
  }

  showMetaContainer(): void {
    if (!this.metaContainer.classList.contains(this.metaExpandedClassName)) {
      this.toggleMetaContainer()
    }
  }

  toggleMetaContainer(e?: Event): void {
    e?.preventDefault()
    e?.stopPropagation()
    this.metaContainer.classList.toggle(this.metaExpandedClassName)
  }

  showAllAttachments(e: Event): void {
    e.preventDefault()
    this.unwrapLeftSibling(e.target as HTMLElement)
  }

  unwrapLeftSibling(el: HTMLElement): void {
    // unwrap left sibling content of parent node
    const parentEl = el?.parentElement
    const outerParent = parentEl?.parentNode
    const previousParent = parentEl?.previousElementSibling
    if (
      el &&
      parentEl != null &&
      outerParent != null &&
      previousParent != null
    ) {
      // move all children out of the element
      while (previousParent.firstChild != null) {
        outerParent.appendChild(previousParent.firstChild)
      }

      // remove the empty element and trigger container
      outerParent.removeChild(parentEl)
      outerParent.removeChild(previousParent)
    }
  }

  scrollToComment(commentElementId: string): void {
    // expand message and comments container first if necessary
    if (!this.isExpanded) {
      this.expandMessage()

      // wait until DOM has finished rendering
      // and scroll to comment element
    }
    ;(function checkIfReady() {
      if (document.readyState === 'complete') {
        const element = document.getElementById(commentElementId)
        if (element == null) return

        // scroll into view
        element.scrollIntoView({ block: 'center', behavior: 'smooth' })

        // add and remove highlight class
        element.classList.add('comments-comment--highlighted')
        setTimeout(() => {
          element.classList.remove('comments-comment--highlighted')
        }, 750)
      } else {
        // if dom not ready, check again on next tick
        window.requestAnimationFrame(checkIfReady)
      }
    })()
  }
}
