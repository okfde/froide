import { Modal } from 'bootstrap'
import { guardSubmits, unsetSubmitting } from '../lib/form-submit'
interface IHTMLModalTriggerElement extends HTMLElement {
  Modal: any | null
}

const confirmForm = (form: HTMLElement): boolean => {
  const confirmMessage = form.dataset.confirm
  if (!confirmMessage) return true
  const confirmed = window.confirm(confirmMessage)
  if (!confirmed) {
    return false
  }
  return true
}

function submitFormsAjax(): void {
  guardSubmits()
  // Listen on the document, so forms added later (e.g. by an ajax response)
  // are handled too
  document.addEventListener('submit', (e) => {
    const form = e.target
    if (!(form instanceof HTMLFormElement) || !form.matches('form.ajaxified')) {
      return
    }
    e.preventDefault()

    if (!confirmForm(form)) {
      unsetSubmitting(form)
      return false
    }

    const method = form.getAttribute('method') || 'post'
    let url = form.getAttribute('action') || ''
    const formData = new FormData(form)
    const data = Array.from(formData)
      .map((pair) => pair.map((x) => encodeURIComponent(x as string)).join('='))
      .join('&')
    if (method.toLowerCase() === 'get') {
      url = `${url}?${data}`
    }
    const request = new XMLHttpRequest()
    request.open(method, url, true)
    request.setRequestHeader(
      'Content-type',
      'application/x-www-form-urlencoded'
    )
    request.setRequestHeader('X-Requested-With', 'XMLHttpRequest')
    request.onload = () => {
      if (form.dataset.modalcontainer) {
        const target = document.querySelector<HTMLElement>(
          form.dataset.modalcontainer
        )
        if (target != null) {
          new Modal(target).show()
          console.log('got modal')
        }
      } else if (form.dataset.modal) {
        const modalTrigger = document.getElementById(
          form.dataset.modal
        ) as IHTMLModalTriggerElement
        if (modalTrigger?.dataset?.bsTarget) {
          Modal.getInstance(
            document.querySelector(modalTrigger.dataset.bsTarget) as HTMLElement
          )?.hide()
        }
      }

      const responseData = request.responseText
      if (responseData[0] === '/' || responseData.startsWith('https://')) {
        // starts with URL, redirect
        window.location.href = responseData
        if (responseData.includes('#')) {
          window.location.reload()
        }
        return
      }
      if (form.dataset.container) {
        unsetSubmitting(form)
        const container = document.querySelector(form.dataset.container)
        if (container != null) {
          container.innerHTML = responseData
        }
      } else {
        const parent = form.closest('.ajax-parent')
        if (parent != null) {
          if (responseData[0] === '{') {
            const data = JSON.parse(responseData)
            if (data.errors) {
              parent.outerHTML = `<div class="alert alert-danger">${
                data.errors as string
              }</div>`
            }
          } else {
            parent.outerHTML = responseData
          }
        } else {
          form.outerHTML = responseData
        }
      }
    }
    request.onerror = () => {
      // Allow retrying when the request could not be made at all
      unsetSubmitting(form)
    }
    if (method.toLowerCase() !== 'get') {
      request.send(data)
    } else {
      request.send()
    }
  })
}

submitFormsAjax()

export default {
  submitFormsAjax
}
