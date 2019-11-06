
const runOnPage = () => {
  const hideParents = document.querySelectorAll('.hideparent')
  Array.from(hideParents).forEach((hideParent) => {
    hideParent.addEventListener('click', function (this: HTMLElement, e) {
      e.preventDefault()
      const parent = this.parentElement
      if (parent) {
        parent.style.display = 'none'
      }
    })
  });

  /* Set all form submit buttons to disabled on form submit */
  const forms = document.querySelectorAll('form.disable-submit')
  Array.from(forms).forEach(form => {
    form.addEventListener('submit', function (this: HTMLFormElement) {
      const form = this
      const buttons = form.querySelectorAll('button[type="submit"]')
      Array.from(buttons).forEach(button => {
        button.setAttribute('disabled', '')
      })
    })
  });

  const inputs = document.querySelectorAll('.honigtopf input')
  Array.from(inputs).forEach(input => {
    input.removeAttribute('required')
  })

}

if (document.readyState === 'loading') {
  window.document.addEventListener('DOMContentLoaded', runOnPage)
} else {
  runOnPage()
}
