
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
}

if (document.readyState === 'loading') {
  window.document.addEventListener('DOMContentLoaded', runOnPage)
} else {
  runOnPage()
}
