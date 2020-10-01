import Message from './Message'

interface MessageMapInterface { [id: string]: Message; }

export default class Timeline {
  element: HTMLElement
  messagesRootElement: HTMLElement
  messageMap: MessageMapInterface

  constructor (
    correspondContainer: HTMLElement,
    timelineContainer: HTMLElement,
    messagesArr: Message[]
  ) {
    this.element = timelineContainer
    this.messagesRootElement = correspondContainer
    this.messageMap = messagesArr.reduce(function(map, obj: Message) {
      map[obj.id] = obj;
      return map;
    }, <MessageMapInterface>{});
    // console.warn('hier', this.messageMap)


    this.setupScrollListener()
    this.setupObserver()
    // setTimeout(() => {
    // }, 1000)
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
    const messagesRootHeight = this.messagesRootElement.clientHeight
    const messagesRootOffsetTop = this.messagesRootElement.offsetTop
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

  setupObserver () {
    let observer = new IntersectionObserver(this.observerCallback.bind(this), {
      threshold: 0.55,
      // rootMargin: '400px 0px -400px 0px'
    })
    Object.values(this.messageMap).forEach(msg => {
      observer.observe(msg.element)
    })
  }

  observerCallback (entries: IntersectionObserverEntry[]) {
    // const activeClassName = 'alpha-timeline__item--active'
    // console.warn(entries)
    for (let i = 0, l = entries.length; i < l; i++) {
      const entry = entries[i]
      const isVisible = entry.isIntersecting || entry.intersectionRatio > 0.55
      const msgId = entry.target.id
      this.messageMap[msgId].isVisible = isVisible



      // get month
      // const msgContainer = entry.target as HTMLElement
      // const timestampStr = msgContainer.dataset.ts
      // if (!timestampStr) {
      //   continue
      // }

      // const timestampDate = new Date(timestampStr)
      // const isoDateStr = timestampDate.toISOString().slice(0, 7) // "2019-12"
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

    // console.warn('hier', this.messageMap)
  }

}