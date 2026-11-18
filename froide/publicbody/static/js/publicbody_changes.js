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
        const items = JSON.parse(value)
        // Choices.js 11 only selects objects passed to setValue if they have
        // selected: true, and skips values that already exist as a choice.
        // So start from an empty store and mark every item as selected.
        choicesInstance.clearStore()
        choicesInstance.setValue(
          items.map((item) => ({
            value: String(item.value),
            label: item.label,
            selected: true
          }))
        )
        // setValue fires no addItem event for an empty list, so update the
        // submitted input directly
        el.value = items.map((item) => item.value).join(',')
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
