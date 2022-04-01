import { Modal } from 'bootstrap.native/dist/bootstrap-native-v4'
interface IHTMLModalTriggerElement extends HTMLElement { Modal: any | null }

const confirmForm = (form: HTMLElement): boolean => {
  const confirmMessage = form.dataset.confirm
  if (!confirmMessage) return true
  const confirmed = window.confirm(confirmMessage)
  if (!confirmed) {
    return false
  }
  return true
}

function submitFormsAjax (): void {
  const ajaxForms = document.querySelectorAll('form.ajaxified');
  (Array.from(ajaxForms) as HTMLFormElement[]).forEach((form) => {
    form.addEventListener('submit', (e) => {
      e.preventDefault()

      if (!confirmForm(form)) {
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
      request.setRequestHeader('Content-type', 'application/x-www-form-urlencoded')
      request.setRequestHeader('X-Requested-With', 'XMLHttpRequest')
      request.onload = () => {
        if (form.dataset.modalcontainer) {
          const target = document.querySelector<HTMLElement>(form.dataset.modalcontainer)
          if (target != null) {
            new Modal(target).show()
            console.log('got modal')
          }
        } else if (form.dataset.modal) {
          const modalTrigger = document.getElementById(form.dataset.modal) as IHTMLModalTriggerElement
          if (modalTrigger) {
            modalTrigger.Modal.hide()
          }
        }

        const responseData = request.responseText
        if (responseData[0] === '/') {
          // starts with URL, redirect
          window.location.href = responseData
          if (responseData.includes('#')) {
            window.location.reload()
          }
          return
        }
        if (form.dataset.container) {
          unsetWorking(form)
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
                parent.outerHTML = `<div class="alert alert-danger">${data.errors as string}</div>`
              }
            } else {
              parent.outerHTML = responseData
            }
          } else {
            form.outerHTML = responseData
          }
        }
      }
      if (method.toLowerCase() !== 'get') {
        request.send(data)
      } else {
        request.send()
      }

      setWorking(form)
    })
  })
}

const SPINNER = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>'

const setWorking = (form: HTMLFormElement): void => {
  Array.from(form.querySelectorAll('button, input')).forEach((el) => {
    if (el.getAttribute('type') === 'submit') {
      el.innerHTML = `${SPINNER}${el.innerHTML}`
    }
    el.setAttribute('disabled', '')
  })
}

const unsetWorking = (form: HTMLFormElement): void => {
  Array.from(form.querySelectorAll('button, input')).forEach((el) => {
    if (el.getAttribute('type') === 'submit') {
      el.innerHTML = el.innerHTML.replace(SPINNER, '')
    }
    el.removeAttribute('disabled')
  })
}

submitFormsAjax()

export default {
  submitFormsAjax
}
