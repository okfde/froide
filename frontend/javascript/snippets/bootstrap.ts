import {
  Alert,
  Collapse,
  Dropdown,
  Modal,
  Offcanvas,
  Tab,
  Tooltip
} from 'bootstrap'

import { collapsePersistent } from '../lib/bootstrap-helpers'

document.addEventListener('DOMContentLoaded', () => {
  document
    .querySelectorAll('[data-bs-toggle="tooltip"]')
    .forEach((el) => new Tooltip(el))
  // see also django-slot.vue
  document
    .querySelectorAll<HTMLElement>('[data-bs-collapse-persistent]')
    .forEach((el) => collapsePersistent(el))
})
;(window as any).bootstrap = {
  Tooltip,
  Alert,
  Dropdown,
  Modal,
  Tab,
  Collapse,
  Offcanvas
}
