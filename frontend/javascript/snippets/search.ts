const firstPathSegment = (path: string) => path.split('/')[1]

document
  .querySelectorAll<HTMLFormElement>('.froide-multi-search')
  .forEach((form) => {
    const select = form.querySelector('select')
    if (select === null) return

    select.addEventListener('change', () => {
      form.action = select.value
    })

    const searchBases = [...select.querySelectorAll('option')].map((o) => [
      firstPathSegment(o.value),
      o.value
    ])
    const currentBase = firstPathSegment(window.location.pathname)
    const bestMatch = searchBases.find((s) => s[0] === currentBase)?.[1]
    console.log(bestMatch)

    if (bestMatch !== undefined) {
      form.action = bestMatch
      select.value = bestMatch
    }
  })
