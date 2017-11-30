function scrollToAnchor (id) {
  window.setTimeout(() => {
    let el = document.getElementById(id)
    if (!el) {
      return
    }
    el.scrollIntoView(true)
  }, 100)
}

export {
  scrollToAnchor
}
