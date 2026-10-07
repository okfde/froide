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

const isSubmitting = (form: HTMLFormElement): boolean =>
  form.hasAttribute(SUBMITTING)

const getStatusRegion = (form: HTMLFormElement): HTMLElement => {
  let region = form.querySelector<HTMLElement>(`.${STATUS_CLASS}`)
  if (region === null) {
    region = document.createElement('p')
    region.className = `${STATUS_CLASS} visually-hidden`
    region.setAttribute('aria-live', 'polite')
    form.appendChild(region)
  }
  return region
}

const setSubmitting = (form: HTMLFormElement): void => {
  form.setAttribute(SUBMITTING, '')
  // The spinner is decorative, so announce the state change. Opt-in, as the
  // status needs to be translated: `data-submitting-status="…"` on the form.
  const status = form.dataset.submittingStatus
  if (status) {
    getStatusRegion(form).textContent = status
  }
}

const unsetSubmitting = (form: HTMLFormElement): void => {
  form.removeAttribute(SUBMITTING)
  const region = form.querySelector<HTMLElement>(`.${STATUS_CLASS}`)
  if (region !== null) {
    region.textContent = ''
  }
}

/*
 * Guard against double submission. Returns false if the form is already being
 * submitted, in which case the event has been cancelled.
 */
const guardSubmit = (form: HTMLFormElement, e: Event): boolean => {
  if (isSubmitting(form)) {
    e.preventDefault()
    return false
  }
  setSubmitting(form)
  return true
}

export { guardSubmit, isSubmitting, setSubmitting, unsetSubmitting }
