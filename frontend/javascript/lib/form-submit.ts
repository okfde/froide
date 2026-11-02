/*
 * Form submit state.
 *
 * Rather than disabling submit buttons while a form is being submitted, we flag
 * the form itself. Disabling a button does not actually prevent a second
 * submission (pressing enter in a form field still submits), and it moves focus
 * away from the button, which is disorienting for keyboard and screen reader
 * users. See https://gomakethings.com/articles/dont-disable-buttons/
 *
 * The flag is a `data-submitting` attribute, so submit buttons can be styled
 * via `form[data-submitting]` while staying focusable and announceable.
 */

const SUBMITTING = 'data-submitting'
const STATUS_CLASS = 'form-submitting-status'
const GUARDED_FORMS = 'form.disable-submit, form.ajaxified'

// TODO: Use a proper i18n library
const strings = {
  de: {
    submitting: 'Wird gesendet …'
  },
  en: {
    submitting: 'Submitting…'
  }
}
const lang = document.documentElement.lang.startsWith('de') ? 'de' : 'en' // works for de-AT, de-CH, etc. as well
const i18n = strings[lang]

const isSubmitting = (form: HTMLFormElement): boolean =>
  form.hasAttribute(SUBMITTING)

const findStatusRegion = (form: HTMLFormElement): HTMLElement | null =>
  form.querySelector<HTMLElement>(`.${STATUS_CLASS}`)

/*
 * Add the (empty) live region that announces the submitting state. Screen
 * readers only announce changes to a live region that was already in the
 * document before its content changed.
 */
const addStatusRegion = (form: HTMLFormElement): HTMLElement => {
  let region = findStatusRegion(form)
  if (region === null) {
    region = document.createElement('p')
    region.className = `${STATUS_CLASS} visually-hidden`
    region.setAttribute('role', 'status')
    region.setAttribute('aria-live', 'polite')
    form.appendChild(region)
  }
  return region
}

const setSubmitting = (form: HTMLFormElement): void => {
  form.setAttribute(SUBMITTING, '')
  // The spinner is decorative, so announce the state change. Forms can
  // override the default text with `data-submitting-status="…"`.
  const status = form.dataset.submittingStatus ?? i18n.submitting
  const region = findStatusRegion(form)
  if (region !== null) {
    region.textContent = status
    return
  }
  // The form was added after page load (e.g. by an ajax response), so it has
  // no live region yet: add it empty and fill it a moment later.
  const newRegion = addStatusRegion(form)
  window.setTimeout(() => {
    if (isSubmitting(form)) {
      newRegion.textContent = status
    }
  }, 100)
}

const unsetSubmitting = (form: HTMLFormElement): void => {
  form.removeAttribute(SUBMITTING)
  const region = findStatusRegion(form)
  if (region !== null) {
    region.textContent = ''
  }
}

/*
 * Guard all `form.disable-submit` and `form.ajaxified` forms against double
 * submission, including forms added later. The listener is on the document in
 * the capture phase, so it runs before any submit listener on the form itself:
 * while a form is being submitted, further submits are cancelled and do not
 * reach those listeners.
 */
const guardSubmits = (): void => {
  document
    .querySelectorAll<HTMLFormElement>(GUARDED_FORMS)
    .forEach(addStatusRegion)
  document.addEventListener(
    'submit',
    (e) => {
      const form = e.target
      if (!(form instanceof HTMLFormElement) || !form.matches(GUARDED_FORMS)) {
        return
      }
      if (isSubmitting(form)) {
        // we are already submitting this form, so cancel the second submit
        e.preventDefault()
        e.stopImmediatePropagation()
        return
      }
      setSubmitting(form)
    },
    { capture: true }
  )
}

export { guardSubmits, isSubmitting, setSubmitting, unsetSubmitting }
