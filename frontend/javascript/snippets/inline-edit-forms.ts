const initInlineEditForms = (): void => {
  document.querySelectorAll<HTMLElement>('[data-inlineedit]').forEach((el) => {
    if (!el.dataset.inlineedit) {
      return
    }
    const targetForm = document.querySelector(
      el.dataset.inlineedit
    ) as HTMLElement
    if (!targetForm) {
      return
    }

    let presentation: HTMLElement | null = null
    if (el.dataset.inlineeditpresentation) {
      presentation = document.querySelector(
        el.dataset.inlineeditpresentation
      ) as HTMLElement
    } else {
      presentation = el.parentElement
    }

    const toggle = (e: MouseEvent): void => {
      e.preventDefault()
      presentation?.classList.toggle('d-none')
      targetForm.classList.toggle('d-none')
      if (targetForm.classList.contains('d-none')) {
        presentation?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      } else {
        targetForm.scrollIntoView({ behavior: 'smooth', block: 'center' })
        if (targetForm.dataset.autofocus) {
          const autoFocus = targetForm.querySelector(
            targetForm.dataset.autofocus
          ) as HTMLInputElement
          if (autoFocus) {
            autoFocus.focus()
          }
        }
      }
    }

    el.addEventListener('click', toggle)

    const cancelButton = targetForm.querySelector(
      '[data-inlineeditcancel]'
    ) as HTMLElement
    if (!cancelButton) {
      return
    }
    cancelButton.addEventListener('click', toggle)
  })
}

if (document.readyState === 'loading') {
  window.document.addEventListener('DOMContentLoaded', initInlineEditForms)
} else {
  initInlineEditForms()
}
