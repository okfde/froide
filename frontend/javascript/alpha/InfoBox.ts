// interface IHTMLToolTipElement extends HTMLInputElement { Tooltip: any | null; }

export default class InfoBox {
  element: HTMLElement
  editButton: HTMLElement | undefined
  copyUrlTrigger: HTMLElement | undefined
  editPanel: HTMLElement | undefined
  infoList: HTMLElement | undefined
  editPanelIsVisible: boolean | undefined

  constructor() {
    this.element = document.getElementById('infobox') as HTMLElement

    this.editButtonClickCallback = this.editButtonClickCallback.bind(this)
    // edit button listener
    this.editButton = this.element.querySelector(
      '.info-box__edit-button'
    ) as HTMLElement
    if (this.editButton) {
      this.editPanel = this.element.querySelector(
        '.info-box__edit-panel'
      ) as HTMLElement
      this.editPanelIsVisible = false
      this.infoList = this.element.querySelector(
        '.info-box__list'
      ) as HTMLElement

      // event listeners
      this.editButton.addEventListener('click', this.editButtonClickCallback)
    }

    // copy short url listener
    this.copyUrlTrigger = this.element.querySelector(
      '.copy-short-url-trigger'
    ) as HTMLElement
    if (this.copyUrlTrigger) {
      this.copyUrlTrigger.addEventListener(
        'click',
        this.copyShortUrlTriggerClickCallback.bind(this)
      )
    }

    this.element
      .querySelectorAll<HTMLElement>('.info-box__edit-link')
      .forEach((link) => {
        link.addEventListener('click', this.editButtonClickCallback)
      })
  }

  showStatus(): void {
    if (this.editPanel?.classList.contains('d-none')) {
      this.editButtonClickCallback()
    }
  }

  showInfoBox(): void {
    if (this.infoList?.classList.contains('d-none')) {
      this.editButtonClickCallback()
    }
  }

  editButtonClickCallback(e?: MouseEvent): void {
    e?.preventDefault()
    if (
      this.editButton != null &&
      this.editPanel != null &&
      this.infoList != null
    ) {
      this.editPanel.classList.toggle('d-none')
      this.infoList.classList.toggle('d-none')
      this.editButton.children[0].classList.toggle('d-none')
      this.editButton.children[1].classList.toggle('d-none')
      this.editPanelIsVisible = !this.editPanelIsVisible
    }
  }

  copyShortUrlTriggerClickCallback(e: MouseEvent): void {
    e.preventDefault()
    const el = e.target as IHTMLToolTipElement

    const url = el.getAttribute('href')
    if (url) {
      this.copyToClipboard(url)
    }

    if (el.Tooltip) {
      const originalTitle = el.title
      el.title = el.dataset.copied || ''
      el.Tooltip.hide()
      const switchTooltip = (): void => {
        el.Tooltip.show()
        el.removeEventListener('hidden.bs.tooltip', switchTooltip)

        window.setTimeout(() => {
          el.Tooltip.hide()
          el.title = originalTitle
        }, 2500)
      }

      el.addEventListener('hidden.bs.tooltip', switchTooltip)
    }
  }

  copyToClipboard(text: string): void {
    const el = document.createElement('textarea')
    el.value = text
    el.setAttribute('readonly', '')
    el.style.position = 'absolute'
    el.style.left = '-9999px'
    document.body.appendChild(el)
    el.select()
    document.execCommand('copy')
    document.body.removeChild(el)
  }
}
