import '../../styles/components/alpha/index.scss'
import Message from './Message'
import Timeline from './Timeline'
import ScrollIndicator from './ScrollIndicator'
import InfoBox from './InfoBox'
import { toggleSlide, addText } from '../lib/misc'
import { Tab, Tooltip } from 'bootstrap.native/dist/bootstrap-native-v4'
import Driver from 'driver.js'
import 'driver.js/dist/driver.min.css'

interface IHTMLTabElement extends HTMLElement { Tab: Tab | undefined }

const initRequestPage = (): void => {
  initSetStatusForm()

  console.debug('Init request page...')

  // init message containers
  const messagesContainer = document.getElementById('correspondence') as HTMLElement
  const messages: Message[] = parseMessageContainers()
  if (messages.length === 0) return

  initInlineEditForms()
  initExpandableDescriptions()

  initMessageMarks()

  // init Info Box
  const infoBox = new InfoBox()
  if (window.location.hash === '#set-status') {
    infoBox.showStatus()
  }

  // init timeline
  // eslint-disable-next-line no-new
  new Timeline(messagesContainer, messages)

  // init ScrollIndicator on mobile view
  // eslint-disable-next-line no-new
  new ScrollIndicator(messagesContainer)

  initTabs()

  initCorrespondenceTopMenu(messagesContainer, messages)

  initReplyForm()

  // if url query parameter found, scroll to comment next
  scrollToAnchor(messages)

  // init reply buttons
  const replyButtonTop = document.getElementById('alpha-reply-button-top')
  const replyButtonBottom = document.getElementById('alpha-reply-button-bottom')
  const writeForm = document.getElementById('write-messages')
  const scrollToWriteForm = (): void => {
    setTimeout(() => {
      writeForm?.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      })
    }, 0)
  }
  writeForm?.addEventListener('show.bs.collapse', scrollToWriteForm, false)
  replyButtonTop?.addEventListener('click', (e) => {
    e.preventDefault()
    goToReplyForm()
  })

  const tabLinks = document.querySelectorAll('a[data-tabgo]')
  Array.from(tabLinks).forEach(tabLink => {
    tabLink.addEventListener('click', function (this: HTMLElement) {
      const hrefAttr = this.attributes.getNamedItem('href')
      if (hrefAttr === null) { return }
      const href = hrefAttr?.value
      const el = document.querySelector(href)
      if (el === null) { return }
      const display = window.getComputedStyle(el, null).display
      if (display === 'none') {
        const navLink = document.querySelector('.nav-link[href="' + href + '"]') as IHTMLTabElement
        if (navLink?.Tab != null) {
          navLink.Tab.show()
        }
      }
    })
  })

  const goToReplyForm = (): void => {
    if (!writeForm?.classList.contains('show')) {
      replyButtonBottom?.click()
    } else {
      scrollToWriteForm()
    }
  }

  const fieldFillLinks = document.querySelectorAll('[data-fieldname]')
  Array.from(fieldFillLinks).forEach(el => {
    el.addEventListener('click', fieldFillLinkClick)
  })

  function fieldFillLinkClick (this: HTMLElement): void {
    if (this.dataset?.value) {
      const sel = `[name="${this.dataset.fieldname as string}"][value="${this.dataset.value}"]`
      const checkbox = document.querySelector(sel)
      if (checkbox != null) {
        checkbox.setAttribute('checked', '')
      }
    }
    if (this.dataset?.addtextfield) {
      addText(this.dataset)
    }
    goToReplyForm()
  }

  document.addEventListener('keydown', function (event) {
    if ((event.ctrlKey || event.metaKey) && (event.key === 'f' || event.key === 'p')) {
      expandAll(messagesContainer, messages, true, true)
    }
  })

  document.querySelectorAll<HTMLElement>('[data-tour]').forEach(t => {
    t.addEventListener('click', (e) => {
      e.stopPropagation()
      infoBox.showInfoBox()
      startTour(t.dataset.tour, t.dataset.tourdone)
    })
  })
}

const startTour = (tourId: string | undefined, tourDoneSelector: string | undefined): void => {
  if (!tourId) {
    return
  }
  const tourDataEl = document.querySelector(`#${tourId}`)
  if ((tourDataEl == null) || !tourDataEl.textContent) {
    return
  }
  let tourData
  try {
    tourData = JSON.parse(tourDataEl.textContent)
  } catch {
    return
  }
  const lastStep = tourData.steps[tourData.steps.length - 1]
  const driver = new Driver({
    animate: true, // Animate while changing highlighted element
    doneBtnText: tourData.i18n.done, // Text on the final button
    closeBtnText: tourData.i18n.close, // Text on the close button for this step
    nextBtnText: tourData.i18n.next, // Next button text for this step
    prevBtnText: tourData.i18n.previous, // Previous button text for this step
    scrollIntoViewOptions: { behavior: 'smooth', block: 'center' },
    onReset: (el: any) => {
      if (el.node === document.querySelector(lastStep.element)) {
        // Done button clicked
        if (tourDoneSelector) {
          const done = document.querySelector(tourDoneSelector) as HTMLElement
          done?.click()
        }
      }
    }
  })
  driver.defineSteps(tourData.steps)
  driver.start()
}

const parseMessageContainers = (): Message[] => {
  const messages: Message[] = []
  const urlHash = window.location.hash
  const collapsedMsgId = /^#nachricht-[0-9]+$/.test(urlHash) ? urlHash.substr(1) : null
  const messageContainers = document.querySelectorAll('.alpha-message')

  messageContainers.forEach((el, idx) => {
    const isLastItem = idx === messageContainers.length - 1
    const forceExpand = collapsedMsgId && collapsedMsgId === el.id
    messages.push(new Message(el as HTMLElement, forceExpand as Boolean, isLastItem as Boolean))
  })
  return messages
}

const initInlineEditForms = (): void => {
  document.querySelectorAll<HTMLElement>('[data-inlineedit]').forEach(el => {
    if (!el.dataset.inlineedit) { return }
    const targetForm = document.querySelector(el.dataset.inlineedit) as HTMLElement
    if (!targetForm) { return }

    let presentation: HTMLElement | null = null
    if (el.dataset.inlineeditpresentation) {
      presentation = document.querySelector(el.dataset.inlineeditpresentation) as HTMLElement
    } else {
      presentation = el.parentElement
    }

    const toggle = (e: MouseEvent): void => {
      e.preventDefault()
      presentation?.classList.toggle('d-none')
      targetForm.classList.toggle('d-none')
      if (targetForm.classList.contains('d-none')) {
        presentation?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      } else {
        targetForm.scrollIntoView({ behavior: 'smooth', block: 'center' })
        if (targetForm.dataset.autofocus) {
          const autoFocus = targetForm.querySelector(targetForm.dataset.autofocus) as HTMLInputElement
          if (autoFocus) {
            autoFocus.focus()
          }
        }
      }
    }

    el.addEventListener('click', toggle)

    const cancelButton = targetForm.querySelector('[data-inlineeditcancel]') as HTMLElement
    if (!cancelButton) { return }
    cancelButton.addEventListener('click', toggle)
  })
}

const initMessageMarks = (): void => {
  document.querySelectorAll<HTMLElement>('[data-messagemark]').forEach((guidance) => {
    const messageMark = guidance.dataset.messagemark
    if (!messageMark || !guidance.dataset.messageid) { return }
    const markObj = JSON.parse(messageMark)
    if (markObj.span) {
      applyMarkToMessage(guidance.dataset.messageid, guidance.id, markObj.span)
    }
  })
}

const applyMarkToMessage = (messageId: string, guidanceId: string, span: number[]): void => {
  const messageText = document.querySelector(`#${messageId} .text-content-visible`)
  if (messageText == null) { return }
  let charIndex = 0
  for (let i = 0; i < messageText.childNodes.length; i++) {
    const node = messageText.childNodes[i]
    console.log(node, guidanceId, span, charIndex)
    const content = node.textContent || ''
    if (span[0] > charIndex && span[0] < charIndex + content.length) {
      const match = content.substring(span[0] - charIndex, span[1] - charIndex)
      const mark = document.createElement('mark')
      mark.dataset.toggle = 'tooltip'
      mark.setAttribute('title', '<i class="fa fa-info-circle"></i>')
      const markA = document.createElement('a')
      markA.href = '#' + guidanceId
      markA.appendChild(document.createTextNode(match))
      mark.appendChild(markA)
      if (node.nodeName === '#text') {
        const textNode = node as Text
        const second = textNode.splitText(span[0] - charIndex)
        messageText.insertBefore(mark, second)
        second.textContent = content.substring(span[1] - charIndex, content.length)
        // eslint-disable-next-line no-new
        new Tooltip(mark)
      }
      return
    }
    if (span[0] < charIndex) {
      // we missed it
      return
    }
    charIndex += content.length
  }
}

const initExpandableDescriptions = (): void => {
  const textContainers = document.querySelectorAll('.request-descr')
  Array.from(textContainers).forEach(textContainer => {
    const readmoreContainer = textContainer.querySelector('.request-descr-read-more')
    const expandButton = textContainer.querySelector('.expand-descr-btn')
    const clientHeight = textContainer?.clientHeight || 0
    const scrollHeight = textContainer?.scrollHeight || 0

    const expand = (): void => {
      readmoreContainer?.classList.add('d-none')
      textContainer?.classList.remove('request-descr--collapsed')
    }

    if (scrollHeight <= clientHeight) {
      expand()
    } else {
      expandButton?.addEventListener('click', () => expand())
    }
  })
}

const scrollToAnchor = (messages: Message[]): void => {
  // when all messages initialized:
  // scroll to comment if query parameters given (e.g. ?msg=76058&c=10856)
  // find message and comment containers with id that equal query params
  const urlParams = new URLSearchParams(window.location.search)
  const msgParam = urlParams.get('msg')
  const commentParam = urlParams.get('c')
  const scrollToMsgId = msgParam ? `nachricht-${msgParam}` : null
  const scrollToCommentId = commentParam ? `comment-${commentParam}` : null
  if (scrollToMsgId && scrollToCommentId) {
    const msg = messages.find(m => m.id === scrollToMsgId)
    if (msg != null) {
      msg.scrollToComment(scrollToCommentId)
    }
    return
  }
  if (window.location.hash) {
    const element = document.querySelector(window.location.hash)
    if (element != null) {
      window.setTimeout(() => {
        element.scrollIntoView({ behavior: 'smooth' })
      }, 300)
    }
  }
}

const initTabs = (): void => {
  const container = document.querySelector('.alpha-tabs') as HTMLElement
  const tabCollection = container.getElementsByTagName('A')
  Array.from(tabCollection).forEach((tab) => {
    // eslint-disable-next-line no-new
    new Tab(tab as HTMLElement, { height: false })
  })

  // show tab if query paramter exists
  let hash = document.location?.hash || ''
  hash = hash.replace(/[^#\-\w]/g, '')
  const hashNav = container.querySelector('a[href="' + hash + '"]') as IHTMLTabElement
  if (hashNav?.Tab != null) {
    hashNav.Tab.show()
    // scroll tab into view
    hashNav.scrollIntoView()
  }
}

const initCorrespondenceTopMenu = (messagesContainer: HTMLElement, messages: Message[]): void => {
  const expandAllLink = document.querySelector('.js-trigger-expand-all-messages') as HTMLElement

  expandAllLink.addEventListener('click', (e: MouseEvent) => {
    e.preventDefault()
    expandAll(messagesContainer, messages)
  })
}

const expandAll = (messagesContainer: HTMLElement, messages: Message[], mustExpand = false, details = false): void => {
  const isAllExpandedClass = 'is-all-expanded'

  if (mustExpand && details) {
    messages.forEach(m => {
      m.showMetaContainer()
    })
  }

  const isAllExpanded = messagesContainer.classList.contains(isAllExpandedClass)
  if (isAllExpanded && mustExpand) {
    return
  }

  // expand or collapse all messages
  for (let i = 0, l = messages.length; i < l; i++) {
    const msg = messages[i]
    if (isAllExpanded) {
      msg.collapseMessage()
    } else {
      msg.expandMessage()
    }
  }

  document.querySelectorAll('.js-trigger-expand-all-messages .fa').forEach(el => {
    el.classList.toggle('d-none-important')
  })
  document.querySelectorAll('.js-trigger-expand-all-messages span').forEach(el => {
    el.classList.toggle('d-none-important')
  })

  // add/remove class to message container
  if (isAllExpanded) {
    messagesContainer.classList.remove(isAllExpandedClass)
  } else {
    messagesContainer.classList.add(isAllExpandedClass)
  }
}

const initSetStatusForm = (): void => {
  const idResolution = document.querySelector('#id_resolution')
  if (idResolution !== null) {
    idResolution.addEventListener('change', setStatus)
  }

  document.querySelectorAll('input[name="status"]').forEach(input => {
    input.addEventListener('change', setStatus)
  })

  setStatus()
}

let refusalInputIsVisible = false
const setStatus = (): void => {
  const container = document.querySelector('.status-refusal') as HTMLElement
  if (container !== null) {
    const resolutionElement = document.querySelector('#id_resolution') as HTMLInputElement
    if (resolutionElement) {
      const resolutionValue = resolutionElement.value
      const resolutionValueTriggersInput = /refus/.exec(resolutionValue) !== null || /partial/.exec(resolutionValue) !== null
      if (
        (refusalInputIsVisible && !resolutionValueTriggersInput) ||
        (!refusalInputIsVisible && resolutionValueTriggersInput)
      ) {
        refusalInputIsVisible = resolutionValueTriggersInput
        toggleSlide(container, 0.5)
      }
    }
  }
}

const initReplyForm = (): void => {
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

  const toggleStickyClass = (): void => {
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

if (document.readyState === 'loading') {
  window.document.addEventListener('DOMContentLoaded', initRequestPage)
} else {
  initRequestPage()
}
