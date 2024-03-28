import { Tooltip } from 'bootstrap'

// TODO: Use a proper i18n library
const strings = {
  de: {
    clickToCopy: 'Zum Kopieren klicken',
    copied: 'Kopiert!',
    error: 'Konnte nicht kopieren.'
  },
  en: {
    clickToCopy: 'Click to copy',
    copied: 'Copied!',
    error: 'Could not copy.'
  }
}
const lang = window.location.pathname.startsWith('/en/') ? 'en' : 'de'
const i18n = strings[lang]

document.querySelectorAll<HTMLElement>('.copy-text').forEach((copyEl) => {
  let i: number

  const tooltip = new Tooltip(copyEl, {
    title: i18n.clickToCopy
  })

  copyEl.addEventListener('click', () => {
    if (i) clearTimeout(i)

    const setTooltipText = (text: string) =>
      tooltip.setContent({ '.tooltip-inner': text })

    const text =
      copyEl.dataset.copyText ??
      copyEl.getAttribute('value') ??
      copyEl.innerText

    navigator.clipboard
      .writeText(text)
      .then(() => {
        setTooltipText(i18n.copied)
      })
      .catch(() => {
        setTooltipText(i18n.error)
      })
      .finally(() => {
        i = window.setTimeout(() => setTooltipText(i18n.clickToCopy), 3000)
      })
  })
})
