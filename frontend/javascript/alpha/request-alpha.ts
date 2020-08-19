import Message from './Message'
import Timeline from './Timeline'


const initMessageContainers = () => {
  const messages: Message[] = []
  const urlHash = window.location.hash
  const collapsedMsgId = /^#nachricht-[0-9]+$/.test(urlHash) ? urlHash.substr(1) : null
  const messageContainers = document.querySelectorAll('.alpha-message')

  messageContainers.forEach((el, idx) => {
    const isLastItem = idx === messageContainers.length  - 1
    const forceExpand = collapsedMsgId && collapsedMsgId === el.id
    messages.push(new Message(el as HTMLElement, forceExpand as Boolean, isLastItem as Boolean))
  })
  return messages
}


const init = () => {
  // init message containers
  const messages: Message[] = initMessageContainers()

  // when all messages initialized:
  // scroll to comment if query parameters given (e.g. ?msg=76058&c=10856)
  // find message and comment containers with id that equal query params
  if (messages.length) {
    const urlParams = new URLSearchParams(window.location.search);
    const msgParam = urlParams.get('msg')
    const commentParam = urlParams.get('c')
    const scrollToMsgId = msgParam ? `nachricht-${msgParam}` : null
    const scrollToCommentId = commentParam ? `comment-${commentParam}` : null
    if (scrollToMsgId && scrollToCommentId) {
      const msg = messages.find(m => m.id === scrollToMsgId)
      if (msg) {
        msg.scrollToComment(scrollToCommentId)
      }
    }
  }

  // init timeline
  const correspRoot = document.getElementById('correspondence')
  const timelineRoot = document.getElementById('timeline')
  if (correspRoot && timelineRoot) {

  }
}


init()