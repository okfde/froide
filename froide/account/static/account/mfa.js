(function () {
  const downloadTXT = document.querySelectorAll("[data-downloadtxt]");
  [...downloadTXT].forEach(element => {
    element.addEventListener("click", () => {
      const txt = element.dataset.downloadtxt
      var c = document.createElement("a");
      c.download = "recovery-code.txt";
      var t = new Blob([txt], {
        type: "text/plain"
      });
      c.href = window.URL.createObjectURL(t);
      c.click();
    })
  })

  const pinInputs = document.querySelectorAll("[data-pininput]");
  const DIGITS = "0123456789";
  [...pinInputs].forEach(pinInput => {
    const name = pinInput.dataset.pininput
    const valueInput = pinInput.querySelector(`[name="${name}"]`)
    const inputs = pinInput.querySelectorAll('[data-pininputdigits] input');
    const digitCount = inputs.length;
    [...inputs].forEach((input, i) => {
      input.addEventListener('paste', (event) => {
        const text = (event.clipboardData || window.clipboardData).getData('text');
        text.split("").slice(0, digitCount).forEach((digit, j) => {
          if (!DIGITS.includes(digit)) {
            return
          }
          let inp = inputs[j]
          if (!inp) {
            return
          }
          inp.value = digit
          if (j === digitCount - 1) {
            if (inp.closest && inp.closest("form")) {
              inp.closest("form").querySelector("button[type='submit']").click()
            }
          }
        })
      })
      input.addEventListener('keydown', (event) => {
        if (event.key === "Backspace") {
          input.value = ''
          if (i !== 0) {
            inputs[i - 1].focus();
          }
        } else if (event.key === "v" && (event.metaKey || event.ctrlKey)) {
          // allow pasting
          return
        } else {
          if (i === inputs.length - 1 && inputs[i].value !== '') {
            return true;
          } else if (DIGITS.includes(event.key)) {
            inputs[i].value = event.key;
            if (i !== inputs.length - 1) inputs[i + 1].focus();
            event.preventDefault();
            valueInput.value = [...inputs].map(inp => inp.value).join("")
            if (valueInput.value.length === 6) {
              if (valueInput.closest && valueInput.closest("form")) {
                valueInput.closest("form").querySelector("button[type='submit']").click()
              }
            }
          } else {
            event.preventDefault()
          }
        }
      })
    })
  })

}())
