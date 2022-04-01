import { toggleSlide, addText } from './lib/misc'
import { Tab, Tooltip } from 'bootstrap.native/dist/bootstrap-native-v4'

interface IHTMLTabElement extends HTMLElement { Tab: Tab | undefined }

const setStatus = (): void => {
  const refusal = document.querySelector('.status-refusal') as HTMLElement
  if (refusal !== null) {
    refusal.style.display = 'none'
    const resolutionElement = document.querySelector<HTMLInputElement>('#id_resolution')
    if (resolutionElement != null) {
      const resolution = resolutionElement.value
      if (/refus/.exec(resolution) !== null || /partial/.exec(resolution) !== null) {
        toggleSlide(refusal, 0.5)
      }
    }
  }
}

const runOnPage = (): void => {
  document.querySelectorAll<HTMLElement>('.comment-form').forEach((el) => {
    el.style.display = 'none'
  })

  const requestNav = document.querySelector('.request-nav') as HTMLElement
  if (requestNav !== null) {
    // let's give the initialization a JavaScript reference for the "target" option
    const tabCollection = requestNav.querySelectorAll<HTMLAnchorElement>('a')
    tabCollection.forEach((tab) => {
      // eslint-disable-next-line no-new
      new Tab(tab, { height: false })
    })
  }

  const idResolution = document.querySelector('#id_resolution')
  if (idResolution !== null) {
    idResolution.addEventListener('change', setStatus)
  }

  const inputStatus = document.querySelector('input[name="status"]')
  if (inputStatus !== null) {
    inputStatus.addEventListener('change', setStatus)
  }

  setStatus()

  const tabLinks = document.querySelectorAll('a[data-tabgo="tab"]')
  Array.from(tabLinks).forEach((tabLink) => {
    tabLink.addEventListener('click', function (this: HTMLElement, e) {
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

      if (this.dataset?.value) {
        const sel = `[name="${this.dataset.name as string}"][value="${this.dataset.value}"]`
        const checkbox = el.querySelector(sel)
        if (checkbox != null) {
          checkbox.setAttribute('checked', '')
        }
      }
      if (this.dataset?.addtextfield) {
        addText(this.dataset)
      }

      if (el.scrollIntoView) {
        e.preventDefault()
        window.setTimeout(() => {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }, 100)
      }
    })
  })

  if (requestNav !== null) {
    const activeTab = requestNav.dataset.activetab
    if (activeTab && activeTab !== 'info') {
      const activeTabElement = requestNav.querySelector('a[href="#' + activeTab + '"]') as IHTMLTabElement
      if (activeTabElement?.Tab != null) {
        activeTabElement.Tab.show()
      }
    } else {
      let hash = document.location?.hash || ''
      hash = hash.replace(/[^#\-\w]/g, '')
      const hashNav = document.querySelector('.request-nav a[href="' + hash + '"]')
      if (hashNav !== null) {
        const tabNav = requestNav.querySelector('a[href="' + hash + '"]') as IHTMLTabElement
        if (tabNav?.Tab != null) {
          tabNav.Tab.show()
        }
      } else if (activeTab !== 'info') {
        const tabNav = requestNav.querySelector('a[href="#info"]') as IHTMLTabElement
        if (tabNav?.Tab != null) {
          tabNav.Tab.show()
        }
      }
    }
  }

  interface IMessageOffsetCache { top: number, height: number, id: string }

  const messages = [] as IMessageOffsetCache[]
  document.querySelectorAll('.message-container').forEach((el) => {
    const rect = el.getBoundingClientRect()
    const offset = rect.top + window.pageYOffset
    messages.push({
      height: rect.height,
      id: el.id,
      top: offset
    })
  })
  let activeMessage = null as string | null
  document.addEventListener('scroll', () => {
    const py = window.pageYOffset
    for (const message of messages) {
      if (py >= message.top && py <= message.top + message.height) {
        if (activeMessage !== message.id) {
          activeMessage = message.id
          const navEls = document.querySelectorAll('.message-timeline-listitem a')
          navEls.forEach((el) => {
            el.classList.remove('active')
          })
          const navEl = document.querySelector('.message-timeline-listitem [href="#' + message.id + '"]')
          if (navEl !== null) {
            navEl.classList.add('active')
          }
        }
        break
      }
    }
  })

  if (!('ontouchstart' in window.document)) {
    document.querySelectorAll<HTMLElement>('.message-timeline-item').forEach((el) => {
      // eslint-disable-next-line no-new
      new Tooltip(el)
    })
  } else {
    const click = function (this: HTMLElement): void {
      this.click()
    }
    document.querySelectorAll('.message-timeline-item').forEach((el) => {
      el.addEventListener('touchstart', click)
    })
  }
}

if (document.readyState === 'loading') {
  window.document.addEventListener('DOMContentLoaded', runOnPage)
} else {
  runOnPage()
}
