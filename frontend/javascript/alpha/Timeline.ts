import Message from './Message'

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

}