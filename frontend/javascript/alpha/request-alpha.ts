import '../../styles/components/alpha/index.scss'
import Message from './Message'
import Timeline from './Timeline'
import ScrollIndicator from './ScrollIndicator'
import InfoBox from './InfoBox'
import { toggleSlide, addText } from '../lib/misc';
import { Tab } from 'bootstrap.native/dist/bootstrap-native-v4';

interface IHTMLTabElement extends HTMLElement { Tab: Tab | undefined; }


const initRequestPage = () => {
  console.debug('Init request page...')

  // init message containers
  const messagesContainer = document.getElementById('correspondence') as HTMLElement
  const messages: Message[] = parseMessageContainers()
  if (!messages.length) return

  initSummaryForm()
  initTagsForm()
  initExpandableDescription()

  // init Info Box
  new InfoBox()

  initSetStatusForm()

  // init timeline
  new Timeline(messagesContainer, messages)

  // init ScrollIndicator on mobile view
  new ScrollIndicator(messagesContainer)

  initTabs()

  initCorrespondenceTopMenu(messagesContainer, messages)

  initReplyForm()

  // if url query parameter found, scroll to comment next
  scrollToComment(messages)

  // init reply buttons
  const replyButtonTop = document.getElementById('alpha-reply-button-top')
  const replyButtonBottom = document.getElementById('alpha-reply-button-bottom')
  const writeForm = document.getElementById('write-message')
  const scrollToWriteForm = () => {
    setTimeout(() => {
      writeForm?.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      })
    }, 0);
  }
  writeForm?.addEventListener('show.bs.collapse', scrollToWriteForm, false);
  replyButtonTop?.addEventListener('click', (e) => {
    e.preventDefault()
    goToReplyForm()
  })

  const goToReplyForm = () => {
    if (!writeForm?.classList.contains('show')) {
      replyButtonBottom?.click()
    } else {
      scrollToWriteForm()
    }
  }

  const fieldFillLinks = document.querySelectorAll('[data-fieldname]') as NodeListOf<HTMLElement>
  Array.from(fieldFillLinks).forEach(el => {
    el.addEventListener('click', fieldFillLinkClick)
  })


  function fieldFillLinkClick (this: HTMLElement) {
    if (this.dataset && this.dataset.value) {
      const sel = '[name="' + this.dataset.fieldname + '"][value="' + this.dataset.value + '"]';
      const checkbox = document.querySelector(sel);
      if (checkbox) {
        checkbox.setAttribute("checked", "");
      }
    }
    if (this.dataset && this.dataset.addtextfield) {
      addText(this.dataset);
    }
    goToReplyForm()
  }

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

const initSummaryForm = () => {
  const buttonsArr = Array.from(document.querySelectorAll('.toggle-summary-form-btn')) as HTMLElement[]
  const editButtonsContainer = document.querySelector('.request-edit-buttons')
  const form = document.querySelector('.request-summary-form')
  const descr = document.querySelector('.request-descr')
  const tags = document.querySelector('.request-tags')
  buttonsArr.forEach(el => {
    el.addEventListener('click', (e: MouseEvent) => {
      e.preventDefault()
      form?.classList.toggle('d-none')
      descr?.classList.toggle('d-none')
      tags?.classList.toggle('d-none')
      editButtonsContainer?.classList.toggle('d-none')
    })

  })
}

const initTagsForm = () => {
  const buttonsArr = Array.from(document.querySelectorAll('.toggle-tags-form-btn')) as HTMLElement[]
  const form = document.querySelector('.request-tags-form')
  const list = document.querySelector('.request-tags-list')
  const editButtonsContainer = document.querySelector('.request-edit-buttons')

  buttonsArr.forEach(el => {
    el.addEventListener('click', (e: MouseEvent) => {
      e.preventDefault()
      form?.classList.toggle('d-none')
      list?.classList.toggle('d-none')
      editButtonsContainer?.classList.toggle('d-none')
    })

  })
}

const initExpandableDescription = () => {
  const textContainer = document.querySelector('.request-descr')
  const readmoreContainer = document.querySelector('.request-descr-read-more')
  const expandButton = document.querySelector('.expand-descr-btn')
  const clientHeight = textContainer?.clientHeight || 0
  const scrollHeight = textContainer?.scrollHeight || 0

  const expand = () => {
    readmoreContainer?.classList.add('d-none')
    textContainer?.classList.remove('request-descr--collapsed')
  }

  if (scrollHeight <= clientHeight) {
    expand()
  } else {
    expandButton?.addEventListener('click', () => expand())
  }
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

const initTabs = () => {
  const container = document.querySelector('.alpha-tabs') as HTMLElement
  const tabCollection = container.getElementsByTagName("A");
  Array.from(tabCollection).forEach((tab) => {
    // tslint:disable-next-line: no-unused-expression
    new Tab(tab as HTMLElement, { height: false });
  })

  // show tab if query paramter exists
  let hash = document.location && document.location.hash || "";
  hash = hash.replace(/[^#\-\w]/g, "");
  const hashNav = container.querySelector('a[href="' + hash + '"]') as IHTMLTabElement;
  if (hashNav !== null && hashNav.Tab) {
    hashNav.Tab.show();
    // scroll tab into view
    hashNav.scrollIntoView()
  }
}

const initCorrespondenceTopMenu = (messagesContainer: HTMLElement, messages: Message[]) => {
  const expandAllLink = document.querySelector('.js-trigger-expand-all-messages') as HTMLElement
  const isAllExpandedClass = 'is-all-expanded'

  expandAllLink.addEventListener('click', (e: MouseEvent) => {
    e.preventDefault()

    const isAllExpanded = messagesContainer.classList.contains(isAllExpandedClass)

    // expand or collapse all messages
    for (let i = 0, l = messages.length; i < l; i++) {
      const msg = messages[i]
      if (isAllExpanded) {
        msg.collapseMessage()
      } else {
        msg.expandMessage()
      }
    }

    // add/remove class to message container
    if (isAllExpanded) {
      messagesContainer.classList.remove(isAllExpandedClass)
    } else {
      messagesContainer.classList.add(isAllExpandedClass)
    }
  })

}

const initSetStatusForm = () => {
  const idResolution = document.querySelector('#id_resolution');
  if (idResolution !== null) {
    idResolution.addEventListener('change', setStatus);
  }

  const inputStatus = document.querySelector('input[name="status"]');
  if (inputStatus !== null) {
    inputStatus.addEventListener('change', setStatus);
  }

  setStatus();

}

let refusalInputIsVisible = false
const setStatus = () => {
  const container = document.querySelector('.status-refusal') as HTMLElement;
  if (container !== null) {
    const resolutionElement = document.querySelector('#id_resolution') as HTMLInputElement;
    if (resolutionElement) {
      const resolutionValue = resolutionElement.value;
      const resolutionValueTriggersInput = /refus/.exec(resolutionValue) !== null || /partial/.exec(resolutionValue) !== null
      if (
        (refusalInputIsVisible && !resolutionValueTriggersInput) ||
        (!refusalInputIsVisible && resolutionValueTriggersInput)
      ) {
        refusalInputIsVisible = resolutionValueTriggersInput
        toggleSlide(container, 0.5);
      }
    }
  }
};

const initReplyForm = () => {
  const replyContainer = document.querySelector('.reply-form') as HTMLElement

  if (!replyContainer) {
    return
  }

  const replyContainerHelper = document.getElementById('reply-form-helper') as HTMLElement
  const replyContainerOffsetTop = replyContainerHelper.offsetTop
  const stickyButton = replyContainer.querySelector('.reply-form__toggle-sticky-btn') as HTMLElement
  let stickyModeEnabled = false
  let userScrolledPastEnd = false


  stickyButton.addEventListener('click', (e: MouseEvent) => {
    e.preventDefault()
    if (stickyModeEnabled) {
      stickyButton.children[0].classList.remove('fa-lock')
      stickyButton.children[0].classList.add('fa-unlock')
      stickyButton.classList.add('btn-link')
      stickyButton.classList.remove('btn-primary')
      replyContainer.classList.remove('reply-form--sticky')
    } else {
      stickyButton.children[0].classList.remove('fa-unlock')
      stickyButton.children[0].classList.add('fa-lock')
      stickyButton.classList.remove('btn-link')
      stickyButton.classList.add('btn-primary')
      if (!userScrolledPastEnd) {
        replyContainer.classList.add('reply-form--sticky')
      }
    }
    stickyModeEnabled = !stickyModeEnabled
  })


  const toggleStickyClass = () => {
    replyContainer.classList.toggle('reply-form--sticky')
  }

  window.addEventListener('scroll', () => {
    const documentScrollTop = document.documentElement.scrollTop
    userScrolledPastEnd = (documentScrollTop + window.innerHeight / 2) >= replyContainerOffsetTop
    const hastStickyClass = replyContainer.classList.contains('reply-form--sticky')
    if (stickyModeEnabled) {
      if (
        (userScrolledPastEnd && hastStickyClass) ||
        (!userScrolledPastEnd && !hastStickyClass)
      ) {
        toggleStickyClass()
      }
    }
  })

}



window.addEventListener('load', initRequestPage)