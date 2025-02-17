import { Tooltip, Toast } from 'bootstrap'
import { collapsePersistent } from './bootstrap-helpers'

/* alternatively, to register globally, we could add to vue-helpers.ts:
   (note also snippets/bootstrap.ts)
  app.directive('bsTooltip', {
    mounted: (el) => {
      new Tooltip(el)
    }
  })
*/
export const vBsTooltip = {
  mounted: (el, binding) => {
    const tooltip = new Tooltip(el)
    if (binding.modifiers['focus-autohide']) {
      el.addEventListener('focusin', () => {
        window.setTimeout(() => tooltip.hide(), 3000)
      })
    }
  }
}

export const vBsCollapsePersistent = {
  mounted: (el) => collapsePersistent(el)
}


export const vBsToast = {
  mounted: (el) => {
    new Toast(el)
  }
}