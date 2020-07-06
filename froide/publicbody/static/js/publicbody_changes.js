(function(){

var proposals = document.querySelectorAll('.proposal')

function applyProposal () {
  var proposalKey = this.value
  var valueElements = document.querySelectorAll(`[data-proposal="${proposalKey}"]`)
  Array.from(valueElements).forEach((valueElement) => {
    var fieldName = valueElement.dataset.field
    var value = valueElement.dataset.value
    var el = document.querySelector(`[name="${fieldName}"]`)
    el.value = value
  })
}

Array.from(proposals).forEach(p => {
  p.addEventListener('change', applyProposal)
})

}())