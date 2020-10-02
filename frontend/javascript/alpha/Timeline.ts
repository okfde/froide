import Message from './Message'

interface TimelineItemsInterface {
  [key: string]: {
    isActive: boolean,
    element: HTMLElement,
    msgCount: number,
    msgVisibleCount: number,
    updateMsgVisibleCount: Function,
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
        msgCount: this.messagesContainer.querySelectorAll(`[data-timeline-key^="${key}"]`)?.length,
        msgVisibleCount: 0,
        updateMsgVisibleCount (increase: boolean) {
          const activeClassName = 'alpha-timeline__item--active'

          if (increase) {
            if (!this.isActive) {
              this.element.classList.add(activeClassName)
              this.isActive = true
            }
            this.msgVisibleCount = this.msgVisibleCount + 1 > this.msgCount
              ? this.msgCount
              : this.msgVisibleCount + 1
          } else {
            this.msgVisibleCount = this.msgVisibleCount - 1 < 0
              ? 0
              : this.msgVisibleCount - 1
            if (this.msgVisibleCount === 0) {
              this.element.classList.remove(activeClassName)
              this.isActive = false
            }
          }

        },
      }

      // element month click event
      const anchorLink: HTMLElement = item.querySelector('.alpha-timeline__month')
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
    const documentScrollTop = document.documentElement.scrollTop
    const messagesRootHeight = this.messagesContainer.clientHeight
    const messagesRootOffsetTop = this.messagesContainer.offsetTop
    const currentScrollPos = documentScrollTop < messagesRootOffsetTop
      ? 0
      : documentScrollTop - messagesRootOffsetTop + document.documentElement.clientHeight
    if (currentScrollPos > 0) {
      const percentageScrolled = (currentScrollPos / messagesRootHeight) * 100
      const innerWrapHeight = this.element.children[0].clientHeight
      const innerWrapScrollPos = ((percentageScrolled * innerWrapHeight) / 100) - (this.element.clientHeight / 2.5)
      this.element.scrollTop = innerWrapScrollPos
      // console.log({currentScrollPos, messagesRootHeight, percentageScrolled, innerWrapScrollPos})
    } else {
      this.element.scrollTop = 0
    }
  }

  setupObserver (messagesArr: Message[]) {
    let observer = new IntersectionObserver(this.observerCallback.bind(this))
    messagesArr.forEach(msg => {
      observer.observe(msg.element)
    })
  }

  observerCallback (entries: IntersectionObserverEntry[]) {
    // const activeClassName = 'alpha-timeline__item--active'
    // console.warn(entries)
    for (let i = 0, l = entries.length; i < l; i++) {
      const entry = entries[i]
      const isVisible = entry.isIntersecting
      // const msgId = entry.target.id



      // get month
      const msgContainer = entry.target as HTMLElement
      const timelineKey = msgContainer.dataset.timelineKey
      if (!timelineKey) {
        continue
      }

      this.items[timelineKey].updateMsgVisibleCount(isVisible)
      // const timelineElement = document.querySelector(`[data-timeline-item^="${isoDateStr}"]`)
      // if (timelineElement) {
      //   if (isVisible) {
      //     timelineElement.classList.add(activeClassName)
      //   } else {
      //     timelineElement.classList.remove(activeClassName)


      //   }

      // }

      // approach with scroll into view
      // if (timelineElement && isVisible) {
      //   console.warn('common', timelineElement)
      //   setTimeout(() => {
      //     timelineElement.scrollIntoView({
      //         behavior: 'smooth',
      //         block: 'start',
      //     })
      //   }, 10);
      // }
    }

    // console.warn('hier', this.items)
  }

}