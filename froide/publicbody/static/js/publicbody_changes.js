;(function () {
  const proposals = document.querySelectorAll('.proposal')

  function applyProposal() {
    const proposalKey = this.value
    const valueElements = document.querySelectorAll(
      `[data-proposal="${proposalKey}"]`
    )
    Array.from(valueElements).forEach((valueElement) => {
      const fieldName = valueElement.dataset.field
      const value = valueElement.dataset.value
      const el = document.querySelector(`[name="${fieldName}"]`)
      if (el.id && window._choices_[el.id] && value) {
        const choicesInstance = window._choices_[el.id]
        const parsedValue = JSON.parse(value)
        choicesInstance.highlightAll().removeHighlightedItems()
        choicesInstance.setValue(parsedValue)
      } else {
        if (value === "None") {
          el.value = ""
        } else {
          el.value = value
        }
      }
    })
  }

  Array.from(proposals).forEach((p) => {
    p.addEventListener('click', applyProposal)
  })


  const formsets = document.querySelectorAll('[data-formset]')
  Array.from(formsets).forEach((formset) => {
    const prefix = formset.dataset.formset
    const template = formset.querySelector('[data-formsetform]')

    const addButton = formset.querySelector('[data-formsetadd]')
    addButton.addEventListener('click', () => {
      const newForm = template.cloneNode(true)
      const totalForms = formset.querySelector('[name$="-TOTAL_FORMS"]')
      const formIndex = parseInt(totalForms.value, 10)
      totalForms.value = formIndex + 1
      
      Array.from(newForm.querySelectorAll('input, select, textarea')).forEach((input) => {
        if (input.name) {
          input.name = input.name.replace(`${prefix}-0-`, `${prefix}-${formIndex}-`)
        }
        if (input.id) {
          input.id = input.id.replace(`${prefix}-0-`, `${prefix}-${formIndex}-`)
        }
        if (input.for) {
          input.for = input.for.replace(`${prefix}-0-`, `${prefix}-${formIndex}-`)
        }
        input.value = ""
      })
      formset.insertBefore(newForm, addButton)
    })
  })
})()
