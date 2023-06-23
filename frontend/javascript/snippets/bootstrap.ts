import {
  Alert,
  Collapse,
  Dropdown,
  Modal,
  Offcanvas,
  Tab,
  Tooltip
} from 'bootstrap'

document.addEventListener('DOMContentLoaded', () => {
  document
    .querySelectorAll('[data-bs-toggle="tooltip"]')
    .forEach((el) => new Tooltip(el))
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
