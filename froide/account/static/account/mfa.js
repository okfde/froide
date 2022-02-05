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
  [...pinInputs].forEach(pinInput => {
    const name = pinInput.dataset.pininput
    const valueInput = pinInput.querySelector(`[name="${name}"]`)
    const inputs = pinInput.querySelectorAll('[data-pininputdigits] input');
    [...inputs].forEach((input, i) => {
      input.addEventListener('keydown', (event) => {
        if (event.key === "Backspace") {
          input.value = ''
          if (i !== 0) {
            inputs[i - 1].focus();
          }
        } else {
          if (i === inputs.length - 1 && inputs[i].value !== '') {
            return true;
          } else if ("0123456789".includes(event.key)) {
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
            event.preventDefault();
          }
        }
      })
    })
  })

}())