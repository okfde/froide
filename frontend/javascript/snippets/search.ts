// multi-search form

const firstPathSegment = (path: string) => path.split('/')[1]

/**
 * Initialize the multi-search component.
 * @param additionalBases Map pages to certain searches, i.e. `[["account", "/requests/"]]` would select the request search on all `/account/*` pages.
 */
export function initSearch(additionalBases: [string, string][] = []) {
  document
    .querySelectorAll<HTMLFormElement>('.froide-multi-search')
    .forEach((form) => {
      const select = form.querySelector('select')
      if (select === null) return

      select.addEventListener('change', () => {
        form.action = select.value
      })

      /*
      the select has options like /documents/search/.
      if the first path segment (here /documents/) of that url matches the
      first path segment of the current window URL, select that option.
    */
      const searchBases = [...select.querySelectorAll('option')].map((o) => [
        firstPathSegment(o.value),
        o.value
      ])
      searchBases.push(...additionalBases)

      const currentBase = firstPathSegment(window.location.pathname)
      const bestMatch = searchBases.find((s) => s[0] === currentBase)?.[1]

      if (bestMatch !== undefined) {
        form.action = bestMatch
        select.value = bestMatch
      }
    })

  // auto-submit form helper
  // form.froide-auto-submit will submit the form when the value of any of its
  // select inputs changes
  document
    .querySelectorAll<HTMLFormElement>('form.froide-auto-submit')
    .forEach((form) => {
      form.querySelectorAll('select').forEach((select) => {
        select.addEventListener('change', () => form.submit())
      })
    })
}
