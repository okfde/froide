import { Tooltip, Toast } from 'bootstrap'
import { collapsePersistent } from './bootstrap-helpers'
import { Directive } from 'vue'

/* alternatively, to register globally, we could add to vue-helpers.ts:
   (note also snippets/bootstrap.ts)
  app.directive('bsTooltip', {
    mounted: (el) => {
      new Tooltip(el)
    }
  })
*/
export const vBsTooltip: Directive<HTMLElement, undefined, 'focus-autohide'> = {
  mounted: (el, binding) => {
    const tooltip = new Tooltip(el)
    if (binding.modifiers['focus-autohide']) {
      el.addEventListener('focusin', () => {
        window.setTimeout(() => tooltip.hide(), 3000)
      })
    }
  }
}

export const vBsCollapsePersistent: Directive<HTMLElement> = {
  mounted: (el) => {
    el.querySelectorAll<HTMLElement>('[data-bs-collapse-persistent]').forEach(
      (el) => collapsePersistent(el)
    )
  }
}

export const vBsToast: Directive<HTMLElement> = {
  mounted: (el) => {
    new Toast(el)
  }
}
