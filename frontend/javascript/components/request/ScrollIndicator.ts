import throttle from 'lodash.throttle'

export default class ScrollIndicator {
  eventAttached: boolean
  messagesContainer: HTMLElement
  maxWidthBreakpoint = 992
  scrollEventCallbackThrottled: EventListenerOrEventListenerObject
  element: HTMLElement
  lineElement: HTMLElement
  elementIsHidden: boolean

  constructor(messagesContainer: HTMLElement) {
    this.messagesContainer = messagesContainer
    this.eventAttached = false
    this.scrollEventCallbackThrottled = throttle(
      this.scrollEventCallback.bind(this),
      75
    ) as EventListenerOrEventListenerObject
    this.element = document.querySelector('.scroll-indicator') as HTMLElement
    this.lineElement = this.element.children[0] as HTMLElement
    this.elementIsHidden = true

    this.setupResizeListener()
  }

  setupResizeListener(): void {
    window.onresize = this.resizeListenerCallback.bind(this)

    // execute on first run
    this.resizeListenerCallback()
  }

  resizeListenerCallback(): void {
    const windowWidth = window.innerWidth
    const eventAttached = this.eventAttached
    const maxWidth = this.maxWidthBreakpoint

    // init / destroy eventAttached
    if (windowWidth < maxWidth && !eventAttached) {
      this.setupScrollListener()
      this.eventAttached = true
    } else if (windowWidth >= maxWidth && eventAttached) {
      this.destroyScrolllListener()
      this.eventAttached = false
    }
  }

  setupScrollListener(): void {
    document.addEventListener('scroll', this.scrollEventCallbackThrottled)
  }

  destroyScrolllListener(): void {
    document.removeEventListener('scroll', this.scrollEventCallbackThrottled)
  }

  scrollEventCallback(): void {
    const pos = this.messagesContainer.getBoundingClientRect()

    if (pos.top > 0) {
      if (!this.elementIsHidden) {
        this.hideIndicator()
      }
      return
    }

    if (this.elementIsHidden) {
      this.showIndicator()
    }

    const scrollTopBottom = pos.top
    const height = pos.height
    const percentageScrolled =
      (Math.abs(scrollTopBottom) / (height - window.innerHeight)) * 100

    this.lineElement.style.width = `${percentageScrolled}%`
  }

  showIndicator(): void {
    this.element.style.opacity = '1'
    this.element.style.visibility = 'visible'
    this.elementIsHidden = false
  }

  hideIndicator(): void {
    this.element.style.opacity = '0'
    this.element.style.visibility = 'hidden'
    this.elementIsHidden = true
  }
}
