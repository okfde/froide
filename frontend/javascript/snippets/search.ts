function applyToForm(searchForm: HTMLFormElement): void {
  function submitForm(): void {
    searchForm.submit()
  }
  const inputs = searchForm.querySelectorAll('select')
  let i
  for (i = 0; i < inputs.length; i += 1) {
    const selectInput = inputs[i]
    selectInput.addEventListener('change', submitForm)
  }

  function dropdownSubmit(input: HTMLInputElement) {
    return function (this: HTMLElement, e: Event) {
      e.preventDefault()
      input.value = this.dataset.value ?? ''
      searchForm.submit()
    }
  }

  const dropdowns = searchForm.querySelectorAll('.dropdown')
  for (i = 0; i < dropdowns.length; i += 1) {
    const dropdown = dropdowns[i]
    const input = dropdown.querySelector('input')
    dropdown.querySelectorAll('.dropdown-menu a').forEach((dropdownLink) => {
      dropdownLink.addEventListener(
        'click',
        dropdownSubmit(input as HTMLInputElement)
      )
    })
  }
}

const domSearchForm = document.querySelector<HTMLFormElement>('.search-form')
if (domSearchForm !== null) {
  applyToForm(domSearchForm)
}

document.addEventListener('shown.bs.modal', (event) => {
  if (event.target == null) {
    return
  }
  if (event.target instanceof HTMLElement) {
    const focussable = event.target.querySelector('[data-focus]')
    if (focussable instanceof HTMLInputElement) {
      focussable.focus()
    }
  }
})
