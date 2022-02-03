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
}())