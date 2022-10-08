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
      if (el.id && window._choices_[el.id]) {
        const choicesInstance = window._choices_[el.id]
        const parsedValue = JSON.parse(value)
        choicesInstance.highlightAll().removeHighlightedItems()
        choicesInstance.setValue(parsedValue)
      } else {
        el.value = value
      }
    })
  }

  Array.from(proposals).forEach((p) => {
    p.addEventListener('click', applyProposal)
  })
})()
