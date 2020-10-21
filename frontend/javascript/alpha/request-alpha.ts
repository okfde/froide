import '../../styles/components/alpha/index.scss'
import Message from './Message'
import Timeline from './Timeline'
import ScrollIndicator from './ScrollIndicator'
import InfoBox from './InfoBox'


const init = () => {
  const messagesContainer = document.getElementById('correspondence')
  const timelineContainer = document.getElementById('timeline')
  const infoboxContainer = document.getElementById('infobox')
  if (!messagesContainer || !timelineContainer || !infoboxContainer) {
    return
  }

  // init message containers
  const messages: Message[] = parseMessageContainers()
  if (!messages.length) return

  // init Info Box
  new InfoBox(infoboxContainer)

  // init timeline
  new Timeline(messagesContainer, timelineContainer, messages)

  // init ScrollIndicator
  new ScrollIndicator(messagesContainer)

  // if url query parameter found, scroll to comment next
  scrollToComment(messages)

}


const parseMessageContainers = () => {
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

const scrollToComment = (messages: Message[]) => {
  // when all messages initialized:
  // scroll to comment if query parameters given (e.g. ?msg=76058&c=10856)
  // find message and comment containers with id that equal query params
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


init()