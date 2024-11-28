import { Tooltip } from 'bootstrap'

/* Note also snippets/bootstrap.ts
   To register globally, we could add to vue-helpers.ts:
     app.directive('bsTooltip', vBsTooltip
   Or, more locally, e.g. in redact.js:
     const app = createAppWithProps...
     app.directive('bsTooltip', vBsTooltip)
     // register directive before mount!
     app.mount...
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
