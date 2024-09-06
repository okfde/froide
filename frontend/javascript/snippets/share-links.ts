// TODO: Use proper i18n library
const strings = {
  de: { error: 'Konnte Inhalt nicht teilen.' },
  en: { error: 'Could not share content.' }
}
const lang = document.documentElement.lang === 'de' ? 'de' : 'en'
const i18n = strings[lang]

document.querySelectorAll<HTMLElement>('.share-native').forEach((btn) => {
  const { shareText: text, shareUrl: url, shareImage } = btn.dataset

  if (shareImage !== undefined) {
    btn.hidden = false

    btn.addEventListener('click', async () => {
      try {
        const r = await fetch(shareImage)
        if (r.status !== 200) throw new Error('Could not load image.')

        const filename = shareImage.split('/').pop()!

        const blob = await r.blob()
        const file = new File([blob], filename, { type: blob.type })

        const shareObj = {
          files: [file]
        }

        try {
          if (navigator.canShare?.(shareObj) === true) {
            navigator.share(shareObj)
          } else {
            throw new Error('Could not share image.')
          }
        } catch {
          const a = document.createElement('a')
          a.href = window.URL.createObjectURL(blob)
          a.download = filename
          a.click()
        }
      } catch (e) {
        console.error(e)
        alert(i18n.error)
      }
    })
  } else {
    const shareObj = { text, url }

    if (navigator.canShare?.(shareObj)) {
      btn.hidden = false

      btn.addEventListener('click', () => {
        navigator.share(shareObj)
      })
    }
  }
})

const storageKey = 'share-mastodon-instance'

document
  .querySelectorAll<HTMLFormElement>('.share-mastodon-form')
  .forEach((form) => {
    const { shareText: text, shareUrl: url } = form.dataset

    const instance = form.querySelector('input')!
    instance.value = localStorage.getItem(storageKey) ?? ''

    form.addEventListener('submit', (e) => {
      e.preventDefault()

      window.open(
        `https://${instance.value}/share?text=${encodeURIComponent(
          text ?? ''
        )}&url=${encodeURIComponent(url ?? '')}`,
        '_blank'
      )
      localStorage.setItem(storageKey, instance.value)
    })
  })
