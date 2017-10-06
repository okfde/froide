/* globals XMLHttpRequest */

class PublicBodySearch {
  constructor (config) {
    this.config = config
  }

  autocomplete (term, filters) {
    return new Promise((resolve, reject) => {
      var request = new XMLHttpRequest()
      let query = encodeURIComponent(term)
      let queryUrl = this.config.url.autocompletePublicBody + '?query=' + query
      request.open('GET', queryUrl, true)
      request.onload = function () {
        let data = JSON.parse(request.responseText)
        if (data.data) {
          resolve(data.data)
        } else {
          reject(request.responseText)
        }
      }
      request.onerror = function () {
        reject(request.statusText)
      }

      request.send()
    })
  }
}

export {
  PublicBodySearch
}
