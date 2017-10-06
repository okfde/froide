/* globals XMLHttpRequest */

class FroideSearch {
  constructor (config) {
    this.config = config
  }

  get (id) {
    return new Promise((resolve, reject) => {
      var request = new XMLHttpRequest()
      let url = this.config.url.getPublicBody.replace(/\/0\//, `/${id}/`)
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

  searchFoiRequests (term) {
    return new Promise((resolve, reject) => {
      var request = new XMLHttpRequest()
      let query = encodeURIComponent(term)
      let queryUrl = this.config.url.searchRequests + '?q=' + query
      request.open('GET', queryUrl, true)
      request.onload = function () {
        let data = JSON.parse(request.responseText)
        if (data.objects) {
          resolve(data.objects)
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
  FroideSearch
}
