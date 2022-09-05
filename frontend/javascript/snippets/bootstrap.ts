import 'bootstrap/js/dist/collapse'
import 'bootstrap/js/dist/tab'
import 'bootstrap/js/dist/modal'
import 'bootstrap/js/dist/dropdown'
import Tooltip from 'bootstrap/js/dist/tooltip'
import Alert from 'bootstrap/js/dist/alert'

const selectors = {
  '[data-bs-toggle="tooltip"]': Tooltip,
  '.alert': Alert
}

document.addEventListener('DOMContentLoaded', () => {
  for (const [selector, Component] of Object.entries(selectors)) {
    document.querySelectorAll(selector).forEach((el) => new Component(el))
  }
})
