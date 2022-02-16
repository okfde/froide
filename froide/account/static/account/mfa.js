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
    const inputLen = parseInt(pinInput.dataset.pininput, 10)
    const submitInput = () => {
      if (pinInput.value.length === inputLen) {
        if (pinInput.closest && pinInput.closest("form")) {
          pinInput.closest("form").querySelector("button[type='submit']").click()
        }
      }
    };
    pinInput.addEventListener('keyup', submitInput)
    pinInput.addEventListener('paste', submitInput)
  })

}())
