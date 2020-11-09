export default class Message {
  id: string
  element: HTMLElement
  metaContainer: HTMLElement
  expandedClassName = 'alpha-message--expanded'

  constructor (element: HTMLElement, forceExpand: Boolean, isLastItem: Boolean) {
    this.id = element.id || ''
    this.element = element
    this.metaContainer = this.element.querySelector('.alpha-message__meta-container') as HTMLElement

    // event listeners

    // header row
    element.querySelector('.alpha-message__head')
      ?.addEventListener('click', this.onHeadClick.bind(this))
    element.querySelector('.alpha-message__meta-toggle')
      ?.addEventListener('click', this.toggleMetaContainer.bind(this))
    element.querySelectorAll('.alpha-comment__more-text-trigger')
      .forEach(el => el.addEventListener('click', this.expandCommentText.bind(this)))
    element.querySelectorAll('.alpha-comment__more-comments-trigger')
      .forEach(el => el.addEventListener('click', this.showAllComments.bind(this)))
    element.querySelectorAll('.alpha-attachment__more-trigger')
      .forEach(el => el.addEventListener('click', this.showAllAttachments.bind(this)))

    // create storage item and/or expand message
    if (!this.storageItem) {
      // create localStorage item
      localStorage.setItem(
        this.id,
        JSON.stringify({ isExpanded: isLastItem || forceExpand })
      )
      // maybe expand
      if (isLastItem || forceExpand) this.expandMessage()
    } else {
      // expand message according to storage state
      if (this.isExpandedInStorage || forceExpand) this.expandMessage()
    }
  }

  get storageItem () {
    const item = localStorage.getItem(this.id)
    return item ? JSON.parse(item) : null
  }

  get isExpandedInStorage () {
    const storageItem = this.storageItem
    return storageItem ? storageItem.isExpanded : false
  }

  updateStorageItem (data: Object) {
    localStorage.setItem(
      this.id,
      JSON.stringify(
        Object.assign(this.storageItem, data)
      )
    )
  }

  onHeadClick (e: Event) {
    this.toggleMessage()
    e.preventDefault()
  }

  toggleMessage () {
    if (this.isExpandedInStorage) {
      this.collapseMessage()
    } else {
      this.expandMessage()
    }
  }

  expandMessage () {
    this.updateStorageItem({ isExpanded: true })
    this.element.classList.add(this.expandedClassName)
  }

  collapseMessage () {
    this.updateStorageItem({ isExpanded: false })
    this.element.classList.remove(this.expandedClassName)
  }

  toggleMetaContainer (e: Event) {
    e.preventDefault()
    e.stopPropagation()
    this.metaContainer.classList.toggle('alpha-message__meta-container--visible')
  }

  expandCommentText (e: Event) {
    e.preventDefault()
    // replace parent node content with right sibling content
    const el = e.target as HTMLElement
    const parentEl = el.parentElement
    if (el && parentEl && el.nextElementSibling) {
      parentEl.innerHTML = el.nextElementSibling.innerHTML
    }
  }

  showAllComments (e?: Event | undefined) {
    let el
    if (e) {
      e.preventDefault()
      el = e.target as HTMLElement
    } else {
      el = this.element.querySelector('.alpha-comment__more-comments-trigger') as HTMLElement
    }

    this.unwrapLeftSibling(el)
  }

  showAllAttachments (e: Event) {
    e.preventDefault()
    this.unwrapLeftSibling(e.target as HTMLElement)
  }

  unwrapLeftSibling (el: HTMLElement) {
    // unwrap left sibling content of parent node
    const parentEl = el?.parentElement
    const outerParent = parentEl?.parentNode
    const previousParent = parentEl?.previousElementSibling
    if (el && parentEl && outerParent && previousParent) {

      // move all children out of the element
      while (previousParent.firstChild) {
        outerParent.appendChild(previousParent.firstChild);
      }

      // remove the empty element and trigger container
      outerParent.removeChild(parentEl);
      outerParent.removeChild(previousParent);
    }
  }

  scrollToComment (commentElementId: string) {
    // expand message and comments container first if necessary
    if (!this.isExpandedInStorage) this.expandMessage()
    this.showAllComments()

    // wait until DOM has finished rendering
    // and scroll to comment element
    ;(function checkIfReady () {
      if (document.readyState === 'complete') {
        const element = document.getElementById(commentElementId)
        if (!element) return

        // scroll into view
        element.scrollIntoView({ block: 'center', behavior: 'smooth' })

        // add and remove highlight class
        element.classList.add('alpha-comment--highlighted')
        setTimeout(() => {
          element.classList.remove('alpha-comment--highlighted')
        }, 750);
      } else (
        // if dom not ready, check again on next tick
        window.requestAnimationFrame(checkIfReady)
      )
    })()

  }

}