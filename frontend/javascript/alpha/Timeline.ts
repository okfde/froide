import Message from './Message'

interface MessageMapInterface { [id: string]: Message; }

export default class Timeline {
  element: HTMLElement
  corrRoot: HTMLElement
  messageMap: MessageMapInterface

  constructor (
    correspondContainer: HTMLElement,
    timelineContainer: HTMLElement,
    messagesArr: Message[]
  ) {
    this.element = timelineContainer
    this.corrRoot = correspondContainer
    this.messageMap = messagesArr.reduce(function(map, obj: Message) {
      map[obj.id] = obj;
      return map;
    }, <MessageMapInterface>{});
    // console.warn('hier', this.messageMap)


    // this.setupScrollListener()
    this.setupObserver()
    // setTimeout(() => {
    // }, 1000)
  }

  // setupScrollListener () {
  //   let timeout: number
  //   window.addEventListener('scroll', () => {
  //     // If there's a timer, cancel it
  //     if (timeout) {
  //       window.cancelAnimationFrame(timeout)
  //     }

  //     // Setup the new requestAnimationFrame()
  //     timeout = window.requestAnimationFrame(this.update.bind(this));
  //   }, false)
  // }

  update () {
    // console.log('debounced', this);
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

      // // get month
      // const msgContainer = entry.target as HTMLElement
      // const timestampStr = msgContainer.dataset.ts
      // if (!timestampStr) {
      //   continue
      // }

      // const timestampDate = new Date(timestampStr)
      // const isoDateStr = timestampDate.toISOString().slice(0, 7) // "2019-12"
      // document.querySelector('.' + activeClassName)?.classList.remove(activeClassName)
      // document.querySelector(`[data-timeline-item^="${isoDateStr}"]`)?.classList.add(activeClassName)
    }

    console.warn('hier', this.messageMap)
  }

}