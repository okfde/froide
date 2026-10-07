import { guardSubmit } from '../lib/form-submit'

/* Flag forms as submitting on submit, so they cannot be submitted twice */
const guardSubmitForms = (): void => {
  document
    .querySelectorAll<HTMLFormElement>('form.disable-submit')
    .forEach((form) => {
      form.addEventListener('submit', (e) => {
        guardSubmit(form, e)
      })
    })
}

if (document.readyState === 'loading') {
  window.document.addEventListener('DOMContentLoaded', guardSubmitForms)
} else {
  guardSubmitForms()
}

export default {
  guardSubmitForms
}
