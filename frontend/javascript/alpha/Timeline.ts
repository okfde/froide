import Message from './Message'

interface TimelineItemsInterface {
  [key: string]: {
    isActive: boolean,
    element: HTMLElement,
    itemsCount: number,
    itemsVisibleCount: number,
    updateItemsVisibleCount: Function,
  };
}

export default class Timeline {
  element: HTMLElement
  messagesContainer: HTMLElement
  items: TimelineItemsInterface

  constructor (
    messagesContainer: HTMLElement,
    timelineContainer: HTMLElement,
    messagesArr: Message[]
  ) {
    this.element = timelineContainer
    this.messagesContainer = messagesContainer
    this.items = this.parseTimelineItems()

    this.setupScrollListener()
    this.setupObserver(messagesArr)

    // setTimeout(() => {
    // }, 1000)
  }

  parseTimelineItems () {
    const result: TimelineItemsInterface = {}
    const nodes: any = this.element.getElementsByClassName('alpha-timeline__item')

    for (let item of nodes) {
      const key = item.dataset.key
      result[key] = {
        isActive: false,
        element: item,
        itemsCount: this.messagesContainer.querySelectorAll(`[data-timeline-key^="${key}"]`)?.length,
        itemsVisibleCount: 0,
        updateItemsVisibleCount (increase: boolean) {
          const activeClassName = 'alpha-timeline__item--active'

          if (increase) {
            if (!this.isActive) {
              this.element.classList.add(activeClassName)
              this.isActive = true
            }
            this.itemsVisibleCount = this.itemsVisibleCount + 1 > this.itemsCount
              ? this.itemsCount
              : this.itemsVisibleCount + 1
          } else {
            this.itemsVisibleCount = this.itemsVisibleCount - 1 < 0
              ? 0
              : this.itemsVisibleCount - 1
            if (this.itemsVisibleCount === 0) {
              this.element.classList.remove(activeClassName)
              this.isActive = false
            }
          }

        },
      }

      // smooth scroll on month click (anchor link)
      const anchorLink: HTMLElement = item.querySelector('.alpha-timeline__month')
      if (anchorLink) {
        anchorLink.addEventListener('click', (e: Event) => {
          e.preventDefault()
          const element = e.target as HTMLElement
          const anchor = element.getAttribute('href')
          if (anchor) {
            document.querySelector(anchor)?.scrollIntoView({
              behavior: 'smooth',
              block: 'start'
            })
          }
        })
      }
    }

    return result
  }

  setupScrollListener () {
    let timeout: number
    window.addEventListener('scroll', () => {
      // If there's a timer, cancel it
      if (timeout) {
        window.cancelAnimationFrame(timeout)
      }

      // Setup the new requestAnimationFrame()
      timeout = window.requestAnimationFrame(this.animationFrameCallback.bind(this));
    }, false)
  }

  animationFrameCallback () {
    // const documentScrollTop = document.documentElement.scrollTop
    // const messagesRootHeight = this.messagesContainer.clientHeight
    // const messagesRootOffsetTop = this.messagesContainer.offsetTop
    // const currentScrollPos = documentScrollTop < messagesRootOffsetTop
    // ? 0
    // : document.documentElement.scrollTop - messagesRootOffsetTop
    // const innerWrapElement = this.element.children[0] as HTMLElement
    // const innerWrapHeight = innerWrapElement.clientHeight
    // const percentValue = currentScrollPos > 0
    //   ? (currentScrollPos / (messagesRootHeight - this.element.clientHeight)) * 100
    //   : 0
    // const percentageScrolled = percentValue <= 100 ? percentValue : 100


    // const innerWrapValue = ((percentageScrolled / 100) * innerWrapHeight) - (this.element.clientHeight / 2.25)
    // // const test = Math.sin(1) * percentageScrolled
    // const scrollValue = innerWrapValue >= 0 ? innerWrapValue : 0

    // console.log({currentScrollPos, innerWrapValue})
    // innerWrapElement.style.transform = `translateY(-${scrollValue}px)`
  }

  setupObserver (messagesArr: Message[]) {
    let observer = new IntersectionObserver(
      this.observerCallback.bind(this),
      { rootMargin: '-50px 0px -50px 0px' }
    )
    messagesArr.forEach(msg => {
      observer.observe(msg.element)
    })
  }

  observerCallback (entries: IntersectionObserverEntry[]) {
    for (let i = 0, l = entries.length; i < l; i++) {
      const entry = entries[i]

      // get month
      const msgContainer = entry.target as HTMLElement
      const timelineKey = msgContainer.dataset.timelineKey
      if (!timelineKey) {
        continue
      }

      const isVisible = entry.isIntersecting
      this.items[timelineKey].updateItemsVisibleCount(isVisible)


    }

    // scroll timeline so that the middle active month is always near the middle of the viewport
    const activeElements = document.querySelectorAll('.alpha-timeline__item--active')
    const activeElement = activeElements[Math.round(activeElements.length / 2)] as HTMLElement
    if (activeElement) {
      // const documentScrollBottom = document.documentElement.scrollTop + document.documentElement.clientHeight
      // const messagesRootOffsetBottom = this.messagesContainer.offsetTop + this.messagesContainer.clientHeight
      // const percentageScrolled = (documentScrollBottom / messagesRootOffsetBottom) * 100

      // const documentScrollTop = document.documentElement.scrollTop
      // const messagesRootOffsetTop = this.messagesContainer.offsetTop
      // if (documentScrollTop < messagesRootOffsetTop) {
      //   return
      // }

      const activeElementOffset = activeElement.offsetTop
      const innerWrapElement = this.element.children[0] as HTMLElement
      const timelineHeight = this.element.clientHeight
      const scrollValue = activeElementOffset > (timelineHeight / 2)
        ? (this.element.clientHeight / 2) - activeElementOffset
        : 0
      innerWrapElement.style.transform = `translateY(${scrollValue}px)`

      // console.log({activeElement, percentageScrolled, documentScrollTop, messagesRootOffsetTop})
      // console.log(this.items)
    }

  }

}