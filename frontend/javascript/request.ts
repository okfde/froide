import {toggleSlide} from './lib/misc'

import {Tab, Tooltip} from 'bootstrap.native'


interface HTMLTabElement extends HTMLElement { Tab: Tab | null; }


const addText = (dataset: DOMStringMap) => {
  if (!dataset.addtextfield) {
    return
  }
  const textField = <HTMLInputElement> document.querySelector(dataset.addtextfield)
  if (textField === null) {
    return
  }
  let text = textField.value
  let addedText = dataset.addtext
  if (!addedText) {
    return
  }
  if (text.indexOf(addedText) !== -1) {
    return
  }
  if (text.indexOf('\n...\n') !== -1) {
    text = text.replace('...', addedText)
  } else {
    let textParts = text.split('\n\n')
    textParts = textParts.slice(0, textParts.length - 1).concat([addedText, textParts[textParts.length - 1]])
    text = textParts.join('\n\n')
  }
  textField.value = text
}

const setStatus = () => {
  const refusal = <HTMLElement> document.querySelector('.status-refusal')
  if (refusal !== null) {
    refusal.style.display = 'none'
    const resolutionElement = <HTMLInputElement> document.querySelector('#id_resolution')
    if (resolutionElement) {
      var resolution = resolutionElement.value
      if (/refus/.exec(resolution) !== null || /partial/.exec(resolution) !== null) {
        toggleSlide(refusal, 0.5)
      }
    }
  }
}

const runOnPage = () => {
  (<HTMLElement[]> Array.from(document.querySelectorAll('.comment-form'))).forEach(el => {
    el.style.display = 'none'
  });

  const requestNav = <HTMLElement> document.querySelector('.request-nav')
  if (requestNav !== null) {
    // let's give the initialization a JavaScript reference for the "target" option
    var myTabsCollection = requestNav.getElementsByTagName('A')
    for (var i = 0; i < myTabsCollection.length; i++) {
      /* eslint-disable no-new */
      new Tab(<HTMLElement> myTabsCollection[i], {height: false})
    }
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
  Array.from(tabLinks).forEach((el) => {
    el.addEventListener('click', function (this: HTMLElement, e) {
      var hrefAttr = this.attributes.getNamedItem('href')
      if (hrefAttr === null) { return }
      var href = hrefAttr && hrefAttr.value
      var el = document.querySelector(href)
      if (el === null) { return }
      var display = window.getComputedStyle(el, null).display
      if (display === 'none') {
        let navLink = <HTMLTabElement> document.querySelector('.nav-link[href="' + href + '"]')
        if (navLink && navLink.Tab) {
          navLink.Tab.show()
        }
      }
      if (el.scrollIntoView) {
        e.preventDefault()
        el.scrollIntoView({behavior: 'smooth'})
      }
  
      if (this.dataset && this.dataset.value) {
        var sel = '[name="' + this.dataset.name + '"][value="' + this.dataset.value + '"]'
        let checkbox = el.querySelector(sel)
        if (checkbox) {
          checkbox.setAttribute('checked', '')
        }
      }
      if (this.dataset && this.dataset.addtextfield) {
        addText(this.dataset)
      }
    })
  })

  if (requestNav !== null) {
    let activeTab = requestNav.dataset.activetab
    if (activeTab && activeTab !== 'info') {
      let activeTabElement = <HTMLTabElement> requestNav.querySelector('a[href="#' + activeTab + '"]')
      if (activeTabElement && activeTabElement.Tab) {
        activeTabElement.Tab.show()
      }
    } else {
      var hash = document.location && document.location.hash || ''
      hash = hash.replace(/[^#\-\w]/g, '')
      var hashNav = document.querySelector('.request-nav a[href="' + hash + '"]')
      if (hashNav !== null) {
        let tabNav = <HTMLTabElement> requestNav.querySelector('a[href="' + hash + '"]')
        if (tabNav && tabNav.Tab) {
          tabNav.Tab.show()
        }
      } else if (activeTab !== 'info') {
        let tabNav = <HTMLTabElement> requestNav.querySelector('a[href="#info"]')
        if (tabNav && tabNav.Tab) {
          tabNav.Tab.show()
        }
      }
    }
  }


  interface MessageOffsetCache { top: number, height: number, id: string }

  var messages = <MessageOffsetCache[]>[]
  document.querySelectorAll('.message-container').forEach(function (el) {
    var rect = el.getBoundingClientRect()
    var offset = rect.top + window.pageYOffset
    messages.push({
      top: offset,
      height: rect.height,
      id: el.id
    })
  })
  var activeMessage = <string | null> null
  document.addEventListener('scroll', function () {
    var py = window.pageYOffset
    for (var i = 0; i < messages.length; i += 1) {
      var message = messages[i]
      if (py >= message.top && py <= message.top + message.height) {
        if (activeMessage !== message.id) {
          activeMessage = message.id
          var navEls = document.querySelectorAll('.message-timeline-listitem a')
          navEls.forEach(function (el) {
            el.classList.remove('active')
          })
          var navEl = document.querySelector('.message-timeline-listitem [href="#' + message.id + '"]')
          if (navEl !== null) {
            navEl.classList.add('active')
          }
        }
        break
      }
    }
  })

  if (!('ontouchstart' in window.document)) {
    Array.from(document.querySelectorAll('.message-timeline-item')).forEach(function (el) {
      new Tooltip(<HTMLElement> el)
    })
  } else {
    var click = function (this: HTMLElement) {
      this.click()
    }
    Array.from(document.querySelectorAll('.message-timeline-item')).forEach(function (el) {
      el.addEventListener('touchstart', click)
    })
  }
}

if (document.readyState === 'loading') {
  window.document.addEventListener('DOMContentLoaded', runOnPage)
} else {
  runOnPage()
}
