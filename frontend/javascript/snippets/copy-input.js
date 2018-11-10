import {Tooltip} from 'bootstrap.native'

document.querySelectorAll('.copy-text').forEach(function (el) {
  el.addEventListener('click', function () {
    let el = this
    el.select()
    document.execCommand('copy')
    if (el.Tooltip) {
      let originalTitle = el.title
      el.Tooltip.hide()
      el.title = this.dataset.copied
      let t = new Tooltip(el)
      t.show()
      window.setTimeout(function () {
        t.hide()
        el.title = originalTitle
      }, 3000)
    }
  })
})
