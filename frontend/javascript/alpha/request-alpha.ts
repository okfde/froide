class Message {
  id: string
  element: HTMLElement
  expandedClassName = 'alpha-message--expanded'
  
  constructor (element: HTMLElement) {
    this.id = 'msg-' + element.id || ''
    this.element = element

    // event listeners

    // header row
    element.querySelector('.alpha-message__head')
      ?.addEventListener('click', this.onHeadClick.bind(this))
    // meta toggle link
    element.querySelector('.alpha-message__meta-toggle')
      ?.addEventListener('click', this.toggleMetaContainer.bind(this))

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
    this.element.classList.add(this.expandedClassName)
  }

  collapseMessage () {
    this.updateStorageItem({ isExpanded: false })
    this.element.classList.remove(this.expandedClassName)
  }

  toggleMetaContainer (e: Event) {
    e.preventDefault()
    e.stopPropagation()
    const containerEl = this.element.querySelector('.alpha-message__meta-container') as HTMLElement
    const visibleClassName = 'alpha-message__meta-container--visible'
    if (containerEl.classList.contains(visibleClassName)) {
      containerEl.classList.remove(visibleClassName)
    } else {
      containerEl.classList.add(visibleClassName)
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