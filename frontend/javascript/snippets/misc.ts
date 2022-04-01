import { scrollToAnchor } from '../lib/misc'

const runOnPage = (): void => {
  document
    .querySelectorAll<HTMLElement>('.hideparent')
    .forEach((hideParent) => {
      hideParent.addEventListener('click', function (this: HTMLElement, e) {
        e.preventDefault()
        const parent = this.parentElement
        if (parent != null) {
          parent.style.display = 'none'
        }
      })
    })

  /* Set all form submit buttons to disabled on form submit */
  const forms = document.querySelectorAll('form.disable-submit')
  Array.from(forms).forEach((f) => {
    f.addEventListener('submit', function (this: HTMLFormElement) {
      this.querySelectorAll<HTMLElement>('button[type="submit"]').forEach(
        (button) => {
          button.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>${button.innerHTML}`
          button.setAttribute('disabled', '')
        }
      )
    })
  })

  document.querySelectorAll<HTMLElement>('[data-teleport]').forEach((el) => {
    let location
    if (el.dataset.teleport) {
      location = document.querySelector(el.dataset.teleport)
    } else {
      location = document.body
    }
    if (location != null) {
      location.appendChild(el)
    }
  })

  document.querySelectorAll<HTMLElement>('[data-scrollto]').forEach((link) => {
    link.addEventListener('click', (e) => {
      if (link.dataset.scrollto) {
        e.preventDefault()
        if (link.dataset.tabgo) {
          window.setTimeout(() => {
            if (link.dataset.scrollto) {
              scrollToAnchor(link.dataset.scrollto, {
                behavior: 'smooth',
                block: link.dataset.scrolltoblock || 'start'
              })
            }
          }, 100)
        } else {
          scrollToAnchor(link.dataset.scrollto, {
            behavior: 'smooth',
            block: link.dataset.scrolltoblock || 'start'
          })
        }
      }
    })
  })

  document.querySelectorAll('.honigtopf input').forEach((input) => {
    input.removeAttribute('required')
  })
}

if (document.readyState === 'loading') {
  window.document.addEventListener('DOMContentLoaded', runOnPage)
} else {
  runOnPage()
}
