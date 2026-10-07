import { Modal } from 'bootstrap'
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
          // When the parent has d-grid, this will not work, we also add d-none
          parent.classList.add('d-none')
        }
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

  document
    .querySelectorAll<HTMLInputElement>('input[data-checkall]')
    .forEach((checkbox) => {
      checkbox.addEventListener('change', () => {
        const checkboxName = checkbox.dataset.checkall
        if (checkboxName == null) {
          return
        }
        document
          .querySelectorAll<HTMLInputElement>(`input[name="${checkboxName}"]`)
          .forEach((el) => {
            el.checked = checkbox.checked
          })
      })
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

  document.querySelectorAll('.modal.modal-show-default').forEach((modal) => {
    Modal.getOrCreateInstance(modal).show()
  })
}

if (document.readyState === 'loading') {
  window.document.addEventListener('DOMContentLoaded', runOnPage)
} else {
  runOnPage()
}
