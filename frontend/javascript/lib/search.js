/* globals XMLHttpRequest */

class FroideSearch {
  constructor (config) {
    this.config = config
  }
  getJson (url) {
    return new Promise((resolve, reject) => {
      var request = new XMLHttpRequest()
      request.open('GET', url, true)
      request.onload = function () {
        if (request.status >= 400) {
          return reject(request.responseText)
        }
        resolve(JSON.parse(request.responseText))
      }
      request.onerror = function () {
        reject(request.statusText)
      }

      request.send()
    })
  }
  getJsonObjects (url) {
    return new Promise((resolve, reject) => {
      this.getJson(url)
        .then((data) => resolve(data.objects))
        .catch((e) => reject(e))
    })
  }
  getPublicBody (id) {
    let url = this.config.url.getPublicBody.replace(/\/0\//, `/${id}/`)
    return this.getJson(url)
  }

  autocompletePublicBody (term) {
    let query = encodeURIComponent(term)
    let url = this.config.url.autocompletePublicBody + '?query=' + query
    return this.getJsonObjects(url)
  }

  searchPublicBody (term) {
    let query = encodeURIComponent(term)
    let url = this.config.url.searchPublicBody + '?q=' + query
    return this.getJsonObjects(url)
  }

  searchFoiRequests (term) {
    let query = encodeURIComponent(term)
    let url = this.config.url.searchRequests + '?q=' + query
    return this.getJsonObjects(url)
  }
}

export {
  FroideSearch
}
