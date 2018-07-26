(function () {
  if (window.opener && window.opener.loggedInCallback) {
    let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value
    window.opener.loggedInCallback({
      csrfToken: csrfToken
    })
  }
}())
