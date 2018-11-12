document.querySelectorAll('.copy-text').forEach(function (el) {
  el.addEventListener('click', function () {
    let el = this
    var selection

    var isiOSDevice = navigator.userAgent.match(/ipad|iphone/i)

    if (isiOSDevice) {
      var editable = el.contentEditable
      var readOnly = el.readOnly

      el.contentEditable = true
      el.readOnly = false

      var range = document.createRange()
      range.selectNodeContents(el)

      selection = window.getSelection()
      selection.removeAllRanges()
      selection.addRange(range)

      el.setSelectionRange(0, 999999)
      el.contentEditable = editable
      el.readOnly = readOnly
    } else {
      el.select()
    }

    document.execCommand('copy')

    if (isiOSDevice) {
      selection.removeAllRanges()
    }

    if (el.Tooltip) {
      let originalTitle = el.title
      el.title = el.dataset.copied
      el.Tooltip.hide()
      var switchTooltip = function () {
        el.Tooltip.show()
        el.removeEventListener('hidden.bs.tooltip', switchTooltip)

        window.setTimeout(function () {
          el.Tooltip.hide()
          el.title = originalTitle
        }, 3000)
      }

      el.addEventListener('hidden.bs.tooltip', switchTooltip)
    }
  })
})
