import Message from './Message'

interface TimelineItemsInterface {
  [key: string]: {
    isActive: boolean
    element: HTMLElement
    msgIdsVisibleMap: MessagesVisbileMap
    updateItemVisibility: Function
  }
}

interface MessagesVisbileMap {
  [key: string]: boolean
}

export default class Timeline {
  element: HTMLElement
  messagesContainer: HTMLElement
  items: TimelineItemsInterface
  lastItemElement: HTMLElement
  firstMessageIsVisible: boolean
  lastMessageIsVisible: boolean
  messagesArr: Message[]
  scrollToEndLink: HTMLElement
  observer: IntersectionObserver | null
  minWidthBreakpoint: number = 992

  constructor (
    messagesContainer: HTMLElement,
    messagesArr: Message[]
  ) {
    this.element = document.getElementById('timeline') as HTMLElement
    this.messagesContainer = messagesContainer
    this.items = this.parseTimelineItems()
    this.lastItemElement = document.querySelector('.alpha-timeline__item--last') as HTMLElement
    this.firstMessageIsVisible = false
    this.lastMessageIsVisible = false
    this.messagesArr = messagesArr
    this.observer = null

    this.scrollToEndLink = this.element.querySelector('.alpha-timeline__scroll-end-link') as HTMLElement
    this.scrollToEndLink?.addEventListener('click', this.scrollToLastMessageLinkCallback.bind(this))
    const otherScrollToEndLink = document.querySelector('.js-trigger-scroll-to-end') as HTMLElement
    otherScrollToEndLink?.addEventListener('click', this.scrollToLastMessageLinkCallback.bind(this))

    this.setupResizeListener()
    this.setupScrollListener()
  }

  scrollToLastMessageLinkCallback (e: MouseEvent) {
    e.preventDefault()
    this.scrollToLastMessage()
  }

  parseTimelineItems () {
    const result: TimelineItemsInterface = {}
    const nodes: any = this.element.getElementsByClassName('alpha-timeline__item')

    for (const item of nodes) {
      const key = item.dataset.key

      result[key] = {
        isActive: false,
        element: item,
        msgIdsVisibleMap: (() => {
          const result: MessagesVisbileMap = {}
          const msgContainersByKey = this.messagesContainer.querySelectorAll(`[data-timeline-key^="${key}"]`)
          const ids = Array.from(msgContainersByKey).map(n => n.id)
          for (let i = 0; i < ids.length; i++) {
            const id: string = ids[i]
            result[id] = false
          }
          return result
        })(),
        updateItemVisibility (msgId: string, isVisible: boolean) {
          const activeClassName = 'alpha-timeline__item--active'

          this.msgIdsVisibleMap[msgId] = isVisible

          // set active if at least one message container is visible
          if (Object.values(this.msgIdsVisibleMap).some(v => v)) {
            this.element.classList.add(activeClassName)
            this.isActive = true
          } else {
            this.element.classList.remove(activeClassName)
            this.isActive = false
          }
        }
      }

      // smooth scroll on link click (anchor link)
      item.querySelector('.alpha-timeline__link')
        .addEventListener('click', this.itemClickCallback.bind(this))
    }

    return result
  }

  itemClickCallback (e: Event) {
    e.preventDefault()
    const target = e.target as HTMLElement
    const element = target.closest('a')
    const anchor = element?.getAttribute('href')
    if (anchor) {
      this.scrollToMessage(anchor)
    }
  }

  getMessageById (id: string) {
    let i = this.messagesArr.length
    const messagesArr = this.messagesArr
    while (i--) {
      if (messagesArr[i].id === id) {
        return messagesArr[i]
      }
    }
  }

  scrollToMessage (anchor: string) {
    // smooth scroll to element
    document.querySelector(anchor)?.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    })

    // expand message if collapsed
    const messageId = anchor.substring(1)
    const messageObj = this.getMessageById(messageId)
    if ((messageObj != null) && messageObj.isCollapsed) {
      messageObj.expandMessage()
    }
  }

  scrollToLastMessage () {
    const messagesArr = this.messagesArr
    const lastMessageId = messagesArr[messagesArr.length - 1].id
    this.scrollToMessage('#' + lastMessageId)
  }

  setupResizeListener () {
    window.addEventListener('resize', this.resizeListenerCallback.bind(this))

    // execute on first run
    this.resizeListenerCallback()
  }

  resizeListenerCallback () {
    const windowWidth = window.innerWidth
    const minWidth = this.minWidthBreakpoint

    // init / destroy observer
    if (windowWidth >= minWidth && this.observer == null) {
      this.setupIntersectionObserver()
    } else if (windowWidth < minWidth && this.observer !== null) {
      this.destroyIntersectionObserver()
    }

    // set timeline height
    if (this.observer !== null) {
      this.setTimelineHeight()
    }
  }

  setupScrollListener () {
    window.addEventListener('scroll', this.scrollListenerCallback.bind(this))

    // execute on first run
    this.scrollListenerCallback()
  }

  get lastTimelineItemIsVisible () {
    // src: https://stackoverflow.com/a/7557433
    const rect = this.lastItemElement.getBoundingClientRect()

    return (
      rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= window.innerHeight &&
        rect.right <= window.innerWidth
    )
  }

  scrollListenerCallback () {
    // toggle scrollToEndLink visibility
    const allTimelineItemsAreInactive = Object.values(this.items).every(item => !item.isActive)
    if (!allTimelineItemsAreInactive) {
      if (this.lastMessageIsVisible || this.lastTimelineItemIsVisible) {
        this.hideScrollToEndLink()
      } else {
        this.showScrollToEndLink()
      }
    }
  }

  setTimelineHeight () {
    // set timeline height to browser window height
    this.element.style.height = window.innerHeight + 'px'
  }

  setupIntersectionObserver () {
    this.observer = new IntersectionObserver(
      this.intersectionObserverCallback.bind(this),
      { rootMargin: '-50px 0px -50px 0px' }
    )
    this.messagesArr.forEach(msg => {
      this.observer?.observe(msg.element)
    })
  }

  destroyIntersectionObserver () {
    this.observer?.disconnect()
    this.observer = null
  }

  hideScrollToEndLink () {
    this.scrollToEndLink.style.opacity = '0'
    this.scrollToEndLink.style.visibility = 'hidden'
  }

  showScrollToEndLink () {
    this.scrollToEndLink.style.opacity = '1'
    this.scrollToEndLink.style.visibility = 'visible'
  }

  intersectionObserverCallback (entries: IntersectionObserverEntry[]) {
    for (let i = 0, l = entries.length; i < l; i++) {
      const entry = entries[i]

      // get month
      const msgContainer = entry.target as HTMLElement
      const timelineKey = msgContainer.dataset.timelineKey
      const msgId = msgContainer.id
      if (!timelineKey || !msgId) {
        continue
      }

      const innerWrapElement = this.element.children[0] as HTMLElement
      const timelineHeight = this.element.clientHeight
      const isVisible = entry.isIntersecting
      this.items[timelineKey].updateItemVisibility(msgId, isVisible)

      if (this.messagesContainer.firstElementChild === msgContainer) {
        this.firstMessageIsVisible = isVisible
      }

      if (this.messagesContainer.lastElementChild === msgContainer) {
        this.lastMessageIsVisible = isVisible
      }

      // scroll timeline so that the center of active months is always in the middle of the viewport
      const activeElements = document.querySelectorAll('.alpha-timeline__item--active')
      const activeElement = activeElements.length === 1
        ? activeElements[0] as HTMLElement
        : activeElements[Math.round(activeElements.length / 2)] as HTMLElement

      if (activeElement) {
        // const documentScrollTop = document.documentElement.scrollTop
        // const messagesRootOffsetTop = this.messagesContainer.offsetTop
        // const isBehindFirstMessage = documentScrollTop > messagesRootOffsetTop
        const activeElementOffset = activeElement.offsetTop
        // const activeElementOffsetPersent = (activeElementOffset / innerWrapElement.clientHeight) * 100
        // console.warn(activeElementOffset, innerWrapElement.clientHeight, maxOffsetPersent)
        const scrollValue = activeElementOffset > (timelineHeight / 2) && !this.firstMessageIsVisible
          ? (this.element.clientHeight / 2) - activeElementOffset
          : 0
        innerWrapElement.style.transform = `translateY(${scrollValue}px)`
      }
    }
  }
}
