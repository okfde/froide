// FIXME: init consistently across components, some don't work yet
import 'bootstrap/js/dist/collapse'
import 'bootstrap/js/dist/tab'
import 'bootstrap/js/dist/modal'
import { Tooltip, Dropdown, Alert } from 'bootstrap'

const selectors = {
  '[data-bs-toggle="tooltip"]': Tooltip,
  '[data-bs-toggle="dropdown"]': Dropdown,
  '.alert': Alert
}

document.addEventListener('DOMContentLoaded', () => {
  for (const [selector, Component] of Object.entries(selectors)) {
    document.querySelectorAll(selector).forEach((el) => new Component(el))
  }
})
