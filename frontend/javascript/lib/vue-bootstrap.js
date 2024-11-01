import { Tooltip } from 'bootstrap'

/* alternatively, to register globally, we could add to vue-helpers.ts:
   (note also snippets/bootstrap.ts)
  app.directive('bsTooltip', {
    mounted: (el) => {
      new Tooltip(el)
    }
  })
*/
export const vBsTooltip = {
  mounted: (el) => {
    new Tooltip(el)
  }
}
