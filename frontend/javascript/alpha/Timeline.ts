import Message from './Message'

// interface IntersectionObserverEntry {
//   isVisible: boolean
// }


export default class Timeline {
  root: HTMLElement
  corrRoot: HTMLElement
  messages: Message[]

  constructor (
    correspondContainer: HTMLElement,
    timelineContainer: HTMLElement,
    messages: Message[]
  ) {
    this.root = timelineContainer
    this.corrRoot = correspondContainer
    this.messages = messages

    this.setupScrollListener()
    setTimeout(() => {

      this.setupObserver()
    }, 1000)
  }

  setupScrollListener () {
    let timeout: number
    window.addEventListener('scroll', () => {
      // If there's a timer, cancel it
      if (timeout) {
        window.cancelAnimationFrame(timeout)
      }

      // Setup the new requestAnimationFrame()
      timeout = window.requestAnimationFrame(this.update.bind(this));
    }, false)
  }

  update () {
    // console.log('debounced', this);
  }

  setupObserver () {
    let observer = new IntersectionObserver(this.observerCallback, {
      threshold: 0.55
    })
    this.messages.forEach(msg => {
      observer.observe(msg.root)
    })
  }

  observerCallback (entries: IntersectionObserverEntry[]) {
    const activeClassName = 'alpha-timeline__item--active'
    for (let i = 0, l = entries.length; i < l; i++) {
      const entry = entries[i]
      if (!entry.isIntersecting || entry.intersectionRatio < 0.55) {
        continue
      }

      // get month
      const msgContainer = entry.target as HTMLElement
      const timestampStr = msgContainer.dataset.ts
      if (!timestampStr) {
        continue
      }

      const timestampDate = new Date(timestampStr)
      const isoDateStr = timestampDate.toISOString().slice(0, 7) // "2019-12"
      document.querySelector('.' + activeClassName)?.classList.remove(activeClassName)
      document.querySelector(`[data-timeline-item^="${isoDateStr}"]`)?.classList.add(activeClassName)
    }
  }

}