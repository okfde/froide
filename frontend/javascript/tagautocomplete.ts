
import '../styles/components/tagautocomplete.scss'

import Choices from 'choices.js'

interface ChoicesSearchEvent extends Event { detail: {value: string}; }


function setupTagging () {
  const allSelects = document.querySelectorAll('.tagautocomplete');
  (<HTMLInputElement[]> Array.from(allSelects)).forEach(select => {
    const selectId = select.id.replace('_select', '')
    const realInput = <HTMLInputElement> document.querySelector('#' + selectId)
    if (realInput === null) {
      return
    }
    const addItemText = select.dataset.additemtext || ''
    const loadingText = select.dataset.loading || ''
    const noResultsText = select.dataset.noresults || ''
    const noChoicesText = select.dataset.nochoices || ''
    const itemSelectText = select.dataset.itemselect || ''
    const uniqueItemText = select.dataset.uniqueitemtext || ''
    const fetchUrl = select.dataset.fetchurl || ''
    
    const choices = new Choices(select, {
      duplicateItemsAllowed: false,
      editItems: true,
      addItems: true,
      delimiter: ',',
      removeItemButton: true,
      addItemText: function(value) {
        return addItemText.replace('${value}', String(value));
      },
      noResultsText,
      loadingText,
      noChoicesText,
      itemSelectText,
      uniqueItemText,
      classNames: {
        hiddenState: 'd-none'
      }
    })

    select.addEventListener('change', function onchange() {
      choices.hideDropdown()
      const value = choices.getValue(true)
      let valueString
      if (Array.isArray(value)) {
        valueString = value.join(', ')
      } else {
        valueString = value
      }
      realInput.value = valueString
    })

    select.addEventListener('search', function onSearch(event) {
      const choicesEvent = <ChoicesSearchEvent> event
      const value = choicesEvent.detail.value
      fetch(fetchUrl + '?query=' + encodeURIComponent(value))
      .then(function(response) {
        response.json().then(function(data: string[]) {
          const present = data.filter((f) => f === value).length > 0
          const transformed = data.map(x => ({value: x, label: x}))
          if (!present) {
            transformed.push({value, label: value})
          }
          choices.setChoices(transformed, 'value', 'label', true);
        });
      })
    })
  })
}






if (document.readyState === 'loading') {
  window.document.addEventListener('DOMContentLoaded', setupTagging)
} else {
  setupTagging()
}

// document.addEventListener('DOMContentLoaded', function () {
//   window.Froide.components.tagautocomplete.setupTagging('%(objectid)s', '%(sourceurl)s', {
//       noResults: '%(noResults)s',
//       searching: '%(searching)s'
//   })
// });




// function setupTagging (objectid, sourceurl, trans) {
//   $(`#${objectid}_select2`).on('change.select2', function (e) {
//     var tagString = $(this).select2('data').map(function (el) {
//       return '"' + el.id + '"'
//     }).join(', ')

//     $(`#${objectid}`).val(tagString)
//   }).select2({
//     width: '75%%',
//     tags: true,
//     language: {
//       noResults: function () {
//         return trans.noResults
//       },
//       searching: function () {
//         return trans.searching
//       }
//     },
//     tokenSeparators: [',', ' '],
//     ajax: {
//       url: sourceurl,
//       data: function (params) {
//         if (params.term.length === 0) {
//           return null
//         }
//         return { query: params.term }
//       },
//       processResults: function (data) {
//         return {
//           results: data.map(function (el) {
//             return { id: el, text: el }
//           })
//         }
//       }
//     }
//   })
// }

// const exp = {
//   setupTagging
// }

// module.exports = exp
// export default exp
