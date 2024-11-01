import { Tab, Tooltip } from 'bootstrap'
import { driver } from 'driver.js'
import 'driver.js/dist/driver.css'
import '../styles/components/request/index.scss'
import InfoBox from './components/request/InfoBox'
import Message from './components/request/Message'
import ScrollIndicator from './components/request/ScrollIndicator'
import Timeline from './components/request/Timeline'
import { addText, toggleSlide } from './lib/misc'

const initRequestPage = (): void => {
  initSetStatusForm()

  console.debug('Init request page...')

  // init message containers
  const messagesContainer =
    document.querySelector<HTMLElement>('#correspondence')!
  const messages: Message[] = parseMessageContainers()
  if (messages.length === 0) return

  initExpandableDescriptions()

  initMessageMarks()

  // init Info Box
  const infoBox = new InfoBox()
  if (window.location.hash === '#set-status') {
    infoBox.showStatus()
  }

  // init timeline
  new Timeline(messagesContainer, messages)

  // init ScrollIndicator on mobile view
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
  replyButtonTop?.addEventListener('click', (e) => {
    e.preventDefault()
    goToReplyForm()
  })

  document
    .querySelectorAll<HTMLAnchorElement>('a[data-tabgo]')
    .forEach((tabLink) => {
      tabLink.addEventListener('click', () => {
        const { hash } = tabLink
        const tab = document.querySelector(hash)
        if (!tab) return

        const { display } = window.getComputedStyle(tab)

        if (display === 'none') {
          const triggerEl = document.querySelector(`.nav-link[href="${hash}"]`)
          Tab.getOrCreateInstance(triggerEl!).show()
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
  fieldFillLinks.forEach((el) => {
    el.addEventListener('click', fieldFillLinkClick)
  })

  function fieldFillLinkClick(this: HTMLElement): void {
    if (this.dataset?.value) {
      const sel = `[name="${this.dataset.fieldname as string}"][value="${
        this.dataset.value
      }"]`
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
    if (
      (event.ctrlKey || event.metaKey) &&
      (event.key === 'f' || event.key === 'p')
    ) {
      expandAll(messagesContainer, messages, true, true)
    }
  })

  window.addEventListener('beforeprint', function () {
    expandAll(messagesContainer, messages, true, true)
  })

  document.querySelectorAll<HTMLElement>('[data-tour]').forEach((t) => {
    t.addEventListener('click', (e) => {
      e.stopPropagation()
      infoBox.showInfoBox()
      startTour(t.dataset.tour, t.dataset.tourdone)
    })
  })

  initWriteMessageButtons()
}

function initWriteMessageButtons(): void {
  document
    .querySelectorAll<HTMLElement>('[data-write-message]')
    ?.forEach((t) => {
      t.addEventListener('click', function () {
        document.getElementById('write-message')?.scrollIntoView()
        const formDataRaw = t?.dataset?.writeMessage
        if (formDataRaw !== undefined) {
          const formData: Record<string, string> = JSON.parse(
            decodeURIComponent(formDataRaw)
          )
          for (const [k, v] of Object.entries(formData)) {
            const elem = document.querySelector<HTMLInputElement>(
              `[name=sendmessage-${k}]`
            )
            if (elem !== null) {
              elem.value = v
            }
          }
        }
      })
    })
}

const startTour = (
  tourId: string | undefined,
  tourDoneSelector: string | undefined
): void => {
  if (!tourId) {
    return
  }

  const tourDataEl = document.querySelector(`#${tourId}`)
  if (tourDataEl === null || !tourDataEl.textContent) {
    return
  }
  const tourData = JSON.parse(tourDataEl.textContent)

  driver({
    animate: true, // Animate while changing highlighted element
    doneBtnText: tourData.i18n.done, // Text on the final button
    nextBtnText: tourData.i18n.next, // Next button text for this step
    prevBtnText: tourData.i18n.previous, // Previous button text for this step
    smoothScroll: true,
    steps: tourData.steps,
    onDestroyed(_el, step) {
      const lastStep = tourData.steps[tourData.steps.length - 1]
      if (step.element === lastStep.element) {
        // Done button clicked
        if (tourDoneSelector) {
          const done = document.querySelector<HTMLElement>(tourDoneSelector)
          done?.click()
        }
      }
    }
  }).drive()
}

const parseMessageContainers = (): Message[] => {
  const messages: Message[] = []
  const urlHash = window.location.hash
  const collapsedMsgId = /^#nachricht-[0-9]+$/.test(urlHash)
    ? urlHash.substr(1)
    : null
  const messageContainers = document.querySelectorAll('.alpha-message')

  messageContainers.forEach((el, idx) => {
    const isLastItem = idx === messageContainers.length - 1
    const forceExpand = collapsedMsgId && collapsedMsgId === el.id
    messages.push(
      new Message(el as HTMLElement, forceExpand as boolean, isLastItem)
    )
  })
  return messages
}

const initMessageMarks = (): void => {
  document
    .querySelectorAll<HTMLElement>('[data-messagemark]')
    .forEach((guidance) => {
      const messageMark = guidance.dataset.messagemark
      if (!messageMark || !guidance.dataset.messageid) {
        return
      }
      const markObj = JSON.parse(messageMark)
      if (markObj.span) {
        applyMarkToMessage(
          guidance.dataset.messageid,
          guidance.id,
          markObj.span
        )
      }
    })
}

const applyMarkToMessage = (
  messageId: string,
  guidanceId: string,
  span: number[]
): void => {
  const messageTexts = document.querySelectorAll(
    `#${messageId} .alpha-message__content-text, #${messageId} .alpha-message__content-text .text-content-visible`
  )
  if (messageTexts.length === 0) {
    return
  }
  const messageText = messageTexts[messageTexts.length - 1]
  let charIndex = 0
  for (let i = 0; i < messageText.childNodes.length; i++) {
    const node = messageText.childNodes[i]
    const content = node.textContent || ''
    if (span[0] > charIndex && span[0] < charIndex + content.length) {
      const match = content.substring(span[0] - charIndex, span[1] - charIndex)
      const mark = document.createElement('mark')
      mark.dataset.toggle = 'tooltip'
      const markA = document.createElement('a')
      markA.href = '#' + guidanceId
      markA.appendChild(document.createTextNode(match))
      mark.appendChild(markA)
      if (node.nodeName === '#text') {
        const textNode = node as Text
        const second = textNode.splitText(span[0] - charIndex)
        messageText.insertBefore(mark, second)
        second.textContent = content.substring(
          span[1] - charIndex,
          content.length
        )

        new Tooltip(mark, {
          html: true,
          title: '<i class="fa fa-info-circle"></i>'
        })
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
  Array.from(textContainers).forEach((textContainer) => {
    const readmoreContainer = textContainer.querySelector(
      '.request-descr-read-more'
    )
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
      expandButton?.addEventListener('click', () => {
        expand()
      })
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
    const msg = messages.find((m) => m.id === scrollToMsgId)
    if (msg != null) {
      msg.scrollToComment(scrollToCommentId)
    }
    return
  }
  if (window.location.hash) {
    let element: HTMLElement | null = null
    try {
      element = document.querySelector(window.location.hash)
    } catch {
      return
    }
    if (element != null) {
      window.setTimeout(() => {
        element?.scrollIntoView({ behavior: 'smooth' })
      }, 300)
    }
  }
}

const initTabs = (): void => {
  const container = document.querySelector<HTMLElement>('.alpha-tabs')
  const tabCollection = container?.querySelectorAll('a')
  tabCollection?.forEach((tab) => {
    new Tab(tab)
  })

  // show tab if query paramter exists
  let hash = document.location?.hash || ''
  hash = hash.replace(/[^#\-\w]/g, '')
  const hashSelector = `a[href="${hash}"]`
  const hashElement = document.querySelector(hashSelector)
  if (hashElement != null) {
    const hashNav = Tab.getInstance(hashSelector)
    if (hashNav != null) {
      hashNav.show()
    } else {
      // Show correspondence tab if hash does not belong to a tab
      const correspondenceTabLink = document.querySelector(
        '#correspondence-tab'
      )
      if (correspondenceTabLink) {
        const tabInstance = Tab.getInstance(correspondenceTabLink)
        tabInstance?.show()
      }
    }
    hashElement.scrollIntoView()
  }
}

const initCorrespondenceTopMenu = (
  messagesContainer: HTMLElement,
  messages: Message[]
): void => {
  const expandAllLink = document.querySelector<HTMLElement>(
    '.js-trigger-expand-all-messages'
  )

  expandAllLink?.addEventListener('click', (e: MouseEvent) => {
    e.preventDefault()
    expandAll(messagesContainer, messages)
  })
}

const expandAll = (
  messagesContainer: HTMLElement,
  messages: Message[],
  mustExpand = false,
  details = false
): void => {
  const isAllExpandedClass = 'is-all-expanded'

  if (mustExpand && details) {
    messages.forEach((m) => {
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

  document
    .querySelectorAll('.js-trigger-expand-all-messages .fa')
    .forEach((el) => {
      el.classList.toggle('d-none-important')
    })
  document
    .querySelectorAll('.js-trigger-expand-all-messages span')
    .forEach((el) => {
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

  document.querySelectorAll('input[name="status"]').forEach((input) => {
    input.addEventListener('change', setStatus)
  })

  setStatus()
}

let refusalInputIsVisible = false
const setStatus = (): void => {
  const container = document.querySelector<HTMLElement>('.status-refusal')
  if (container !== null) {
    const resolutionElement =
      document.querySelector<HTMLInputElement>('#id_resolution')
    if (resolutionElement != null) {
      const resolutionValue = resolutionElement.value
      const resolutionValueTriggersInput =
        /refus/.exec(resolutionValue) !== null ||
        /partial/.exec(resolutionValue) !== null
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
  const replyContainer = document.querySelector<HTMLElement>('.reply-form')

  if (replyContainer == null) {
    return
  }

  const replyContainerHelper =
    document.querySelector<HTMLElement>('#reply-form-helper')!
  const replyContainerOffsetTop = replyContainerHelper.offsetTop
  const stickyButton = replyContainer.querySelector<HTMLElement>(
    '.reply-form__toggle-sticky-btn'
  )!
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
    userScrolledPastEnd =
      documentScrollTop + window.innerHeight / 2 >= replyContainerOffsetTop
    const hastStickyClass =
      replyContainer.classList.contains('reply-form--sticky')
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
