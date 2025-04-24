import '../styles/components/tagautocomplete.scss'

import Choices from 'choices.js'

interface IChoicesSearchEvent extends Event {
  detail: { value: string }
}

interface AutocompleteItem {
  value: string
  label: string
}

interface AutocompleteResponse {
  objects: AutocompleteItem[]
}

declare global {
   
  interface Window {
    _choices_: Record<string, Choices>
  }
}

function setupTagging(): void {
  window._choices_ = window._choices_ ?? {}
  document
    .querySelectorAll<HTMLInputElement>('.tagautocomplete')
    .forEach((select) => {
      const selectId = select.id.replace('_select', '')
      const realInput = document.querySelector<HTMLInputElement>('#' + selectId)
      if (realInput === null) {
        return
      }
      const addItemText = select.dataset.additemtext ?? ''
      const allowNew = select.dataset.allownew === 'true'
      const loadingText = select.dataset.loading ?? ''
      const noResultsText = select.dataset.noresults ?? ''
      const noChoicesText = select.dataset.nochoices ?? ''
      const itemSelectText = select.dataset.itemselect ?? ''
      const uniqueItemText = select.dataset.uniqueitemtext ?? ''
      const fetchUrl = select.dataset.fetchurl ?? ''
      const queryParam = select.dataset.queryparam ?? 'q'
      const maxItemCount = parseInt(select.dataset.maxitemcount ?? '-1') ?? -1

      const choices = new Choices(select, {
        addItemText(value) {
           
          return addItemText.replace('${value}', value)
        },
        addItems: true,
        delimiter: ',',
        duplicateItemsAllowed: false,
        editItems: true,
        maxItemCount,
        itemSelectText,
        loadingText,
        noChoicesText,
        noResultsText,
        searchResultLimit: 8,
        removeItemButton: true,
        uniqueItemText
      })

      window._choices_[selectId] = choices

      const setRealInput = (): void => {
        choices.hideDropdown()
        const value = choices.getValue(true)
        let valueString
        if (value == null) {
          valueString = ''
        } else if (Array.isArray(value)) {
          valueString = value.join(',')
        } else {
           
          valueString = value.toString()
        }
        realInput.value = valueString ?? ''
      }
      select.addEventListener('addItem', setRealInput)
      select.addEventListener('removeItem', setRealInput)

      select.addEventListener('search', function onSearch(event) {
        const choicesEvent = event as IChoicesSearchEvent
        const searchValue = choicesEvent.detail.value
        if (fetchUrl !== '') {
          const url = new URL(fetchUrl, window.location.origin)
          url.searchParams.set(queryParam, searchValue)
          void fetch(url.href).then((response) => {
            void response.json().then((response: AutocompleteResponse) => {
              const data = response.objects
              let currentValue = choices.getValue(true) as string[] | string
              if (!Array.isArray(currentValue)) {
                currentValue = [currentValue]
              }
              const present =
                data.filter((f) => currentValue.includes(f.value)).length > 0
              if (!present && allowNew) {
                data.push({ value: searchValue, label: searchValue })
              }
               
              choices.setChoices(data, 'value', 'label', true)
            })
          })
        } else {
           
          choices.setChoices(
            [{ value: searchValue, label: searchValue }],
            'value',
            'label',
            true
          )
        }
      })
    })
}

if (document.readyState === 'loading') {
  window.document.addEventListener('DOMContentLoaded', setupTagging)
} else {
  setupTagging()
}
