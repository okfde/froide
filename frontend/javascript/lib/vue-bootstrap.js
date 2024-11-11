import { Tooltip } from 'bootstrap'

/* alternatively, to register globally, we could add to vue-helpers.ts:
   (note also snippets/bootstrap.ts)
   (see also redact.js for less global, Options API application)
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
