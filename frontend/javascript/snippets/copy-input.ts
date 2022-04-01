interface IHTMLToolTipElement extends HTMLInputElement {
  Tooltip: any | null
}

document.querySelectorAll('.copy-text').forEach((copyEl) => {
  copyEl.addEventListener('click', function(this: IHTMLToolTipElement) {
    let selection

    const isiOSDevice = navigator.userAgent.match(/ipad|iphone/i)

    if (isiOSDevice != null) {
      const editable = this.contentEditable
      const readOnly = this.readOnly

      this.contentEditable = ''
      this.readOnly = false

      const range = document.createRange()
      range.selectNodeContents(this)

      selection = window.getSelection()
      if (selection !== null) {
        selection.removeAllRanges()
        selection.addRange(range)
      }
      this.setSelectionRange(0, 999999)
      this.contentEditable = editable
      this.readOnly = readOnly
    } else {
      this.select()
    }

    document.execCommand('copy')

    if (isiOSDevice != null && selection != null) {
      selection.removeAllRanges()
    }

    if (this.Tooltip !== undefined) {
      const originalTitle = this.title
      this.title = this.dataset.copied ?? ''
      this.Tooltip.hide()
      const switchTooltip = (): void => {
        this.Tooltip.show()
        this.removeEventListener('hidden.bs.tooltip', switchTooltip)

        window.setTimeout(() => {
          this.Tooltip.hide()
          this.title = originalTitle
        }, 3000)
      }

      this.addEventListener('hidden.bs.tooltip', switchTooltip)
    }
  })
})
