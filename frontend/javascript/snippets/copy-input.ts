interface IHTMLToolTipElement extends HTMLInputElement { Tooltip: any | null; }

Array.from(document.querySelectorAll(".copy-text")).forEach((copyEl) => {
  copyEl.addEventListener("click", function(this: IHTMLToolTipElement) {
    const el = this;
    let selection;

    const isiOSDevice = navigator.userAgent.match(/ipad|iphone/i);

    if (isiOSDevice) {
      const editable = el.contentEditable;
      const readOnly = el.readOnly;

      el.contentEditable = "";
      el.readOnly = false;

      const range = document.createRange();
      range.selectNodeContents(el);

      selection = window.getSelection();
      if (selection !== null) {
        selection.removeAllRanges();
        selection.addRange(range);
      }
      el.setSelectionRange(0, 999999);
      el.contentEditable = editable;
      el.readOnly = readOnly;
    } else {
      el.select();
    }

    document.execCommand("copy");

    if (isiOSDevice && selection) {
      selection.removeAllRanges();
    }

    if (el.Tooltip) {
      const originalTitle = el.title;
      el.title = el.dataset.copied || "";
      el.Tooltip.hide();
      const switchTooltip = () => {
        el.Tooltip.show();
        el.removeEventListener("hidden.bs.tooltip", switchTooltip);

        window.setTimeout(() => {
          el.Tooltip.hide();
          el.title = originalTitle;
        }, 3000);
      };

      el.addEventListener("hidden.bs.tooltip", switchTooltip);
    }
  });
});
