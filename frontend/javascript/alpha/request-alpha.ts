class Message {
  id: string
  root: HTMLElement
  metaContainer: HTMLElement
  expandedClassName = 'alpha-message--expanded'
  
  constructor (element: HTMLElement) {
    this.id = 'msg-' + element.id || ''
    this.root = element
    this.metaContainer = this.root.querySelector('.alpha-message__meta-container') as HTMLElement

    // event listeners

    // header row
    element.querySelector('.alpha-message__head')
      ?.addEventListener('click', this.onHeadClick.bind(this))
    element.querySelector('.alpha-message__meta-toggle')
      ?.addEventListener('click', this.toggleMetaContainer.bind(this))
    element.querySelectorAll('.alpha-message__expand-comment-trigger')
      .forEach(el => el.addEventListener('click', this.expandComment.bind(this)))

    // create localStorage item
    if (!this.storageItem) {
      localStorage.setItem(this.id, JSON.stringify({
        isExpanded: false
      }))
    } else {
      // expand message according to localStorage state 
      if (this.isExpanded) {
        this.expandMessage()
      }
    }
  }

  get storageItem () {
    const item = localStorage.getItem(this.id)
    return item ? JSON.parse(item) : null
  }

  get isExpanded () {
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
    if (this.isExpanded) {
      this.collapseMessage()
    } else {
      this.expandMessage()
    }    
  }

  expandMessage () {
    this.updateStorageItem({ isExpanded: true })
    this.root.classList.add(this.expandedClassName)
  }

  collapseMessage () {
    this.updateStorageItem({ isExpanded: false })
    this.root.classList.remove(this.expandedClassName)
  }

  toggleMetaContainer (e: Event) {
    e.preventDefault()
    e.stopPropagation()
    this.metaContainer.classList.toggle('alpha-message__meta-container--visible')
  }
  
  expandComment (e: Event) {
    e.preventDefault()
    // replace parent node content with right sibling content
    const el = e.target as HTMLElement
    const parentEl = el.parentElement
    if (el && parentEl && el.nextElementSibling) {
      parentEl.innerHTML = el.nextElementSibling.innerHTML
    }
  }

}


const init = () => {
  const messages = []
  document.querySelectorAll('.alpha-message').forEach(el => {
    messages.push(new Message(el as HTMLElement))
  })
  
}


init()