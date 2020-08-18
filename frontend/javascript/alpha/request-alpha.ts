import '../../styles/components/alpha/index.scss'

class Message {
  id: string
  root: HTMLElement
  metaContainer: HTMLElement
  expandedClassName = 'alpha-message--expanded'
  
  constructor (element: HTMLElement, forceExpand: Boolean, isLastItem: Boolean) {
    this.id = element.id || ''
    this.root = element
    this.metaContainer = this.root.querySelector('.alpha-message__meta-container') as HTMLElement

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
      el = this.root.querySelector('.alpha-comment__more-comments-trigger') as HTMLElement
    }
    
    this.unwrapLeftSibling(el)
  }

  showAllAttachments (e: Event) {
    e.preventDefault()
    this.unwrapLeftSibling(e.target as HTMLElement)
  }

  unwrapLeftSibling (el: HTMLElement) {
    // unwrap left sibling content of parent node
    console.warn(el)
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
    const element = document.getElementById(commentElementId)
    if (element) {
      element.scrollIntoView({ block: 'center', behavior: 'smooth' })

      // add and remove highlight class
      element.classList.add('alpha-comment--highlighted')
      setTimeout(() => {
        element.classList.remove('alpha-comment--highlighted')        
      }, 750);
    }
  }

}



const init = () => {
  // init message containers
  const messages: Message[] = []
  const urlHash = window.location.hash
  const collapsedMsgId = /^#nachricht-[0-9]+$/.test(urlHash) ? urlHash.substr(1) : null
  const messageContainers = document.querySelectorAll('.alpha-message')

  messageContainers.forEach((el, idx) => {
    const isLastItem = idx === messageContainers.length  - 1
    const forceExpand = collapsedMsgId && collapsedMsgId === el.id
    messages.push(new Message(el as HTMLElement, forceExpand as Boolean, isLastItem as Boolean))
  })

  // when all messages initialized:
  // scroll to comment if query parameters given
  // find message with id that equals query param
  const urlParams = new URLSearchParams(window.location.search);
  const msgParam = urlParams.get('msg')
  const commentParam = urlParams.get('c')
  const scrollToMsgId = msgParam ? `nachricht-${msgParam}` : null
  const scrollToCommentId = commentParam ? `comment-${commentParam}` : null

  if (messages.length && scrollToMsgId && scrollToCommentId) {
    const msg = messages.find(m => m.id === scrollToMsgId)
    if (msg) {
      if (!msg.isExpandedInStorage) {
        msg.expandMessage()
      }
      msg.showAllComments();

      // wait until DOM has finished rendering
      // and scroll to comment
      (function checkIfReady () {
        if (document.readyState === 'complete') {
          if (document.getElementById(scrollToCommentId)) {
            msg.scrollToComment(scrollToCommentId)
          }
        } else (
          window.requestAnimationFrame(checkIfReady)
        )
      })()
      
    }
  }
  
}


// init()
document.addEventListener("DOMContentLoaded", init)