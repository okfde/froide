import {
  Alert,
  Collapse,
  Dropdown,
  Modal,
  Offcanvas,
  Tab,
  Tooltip
} from 'bootstrap'

import { registerBs } from '../lib/bootstrap-helpers'

document.addEventListener('DOMContentLoaded', () => registerBs(document))

;(window as any).bootstrap = {
  Tooltip,
  Alert,
  Dropdown,
  Modal,
  Tab,
  Collapse,
  Offcanvas
}
