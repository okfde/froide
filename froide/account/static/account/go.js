const autoSubmitForm = document.querySelector("form[data-autosubmit]")
if (autoSubmitForm) {
  const button = autoSubmitForm.querySelector('button[type="submit"]')
  if (button) {
    button.style.display = "none"
  }
  autoSubmitForm.submit()
}
