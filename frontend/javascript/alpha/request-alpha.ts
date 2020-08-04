class Message {
  id: string
  element: HTMLElement
  expandedClassName = 'alpha-message--expanded'
  
  constructor (element: HTMLElement) {
    this.id = 'msg-' + element.dataset.id || ''
    this.element = element

    // event listeners

    // header row
    element.querySelector('.alpha-message__head')
      ?.addEventListener('click', this.onHeadClick.bind(this))
    // details link
    element.querySelector('.alpha-message__details-link')
      ?.addEventListener('click', this.toggleDetailsContainer.bind(this))

    // create localStorage item
    if (!this.storageItem) {
      localStorage.setItem(this.id, JSON.stringify({
        isExpanded: false
      }))
    } else {
      // expand message according to localStorage state 
      if (this.isExpanded) {
        this.expand()
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
    const el = e.target as HTMLElement
    if (el.closest('.alpha-message__sender-link')) {
      // user clicked sender link
      return
    }
  
    this.toggleExpand()
    e.preventDefault()
  }

  toggleExpand () {
    if (this.isExpanded) {
      this.collapse()
    } else {
      this.expand()
    }    
  }

  expand () {
    this.updateStorageItem({ isExpanded: true })
    this.element.classList.add(this.expandedClassName)
  }

  collapse () {
    this.updateStorageItem({ isExpanded: false })
    this.element.classList.remove(this.expandedClassName)
  }

  toggleDetailsContainer (e: Event) {
    e.preventDefault()
    e.stopPropagation()
    const containerEl = this.element.querySelector('.alpha-message__details-container') as HTMLElement
    if (!containerEl.style.display) {
      containerEl.style.display = 'block'
    } else {
      containerEl.style.display = ''
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