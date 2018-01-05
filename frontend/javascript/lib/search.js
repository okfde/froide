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
  getObjects (promise) {
    return new Promise((resolve, reject) => {
      promise.then((data) => {
        return resolve(data.objects)
      })
        .catch((e) => reject(e))
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

  getJsonForUrl (url, term, filters) {
    let hasParam = false
    if (term !== undefined && term) {
      hasParam = true
      url = url + '?q=' + encodeURIComponent(term)
    }
    if (filters !== undefined) {
      let f = []
      for (let key in filters) {
        let filterVal = filters[key]
        if (filterVal !== null) {
          if (!Array.isArray(filterVal)) {
            filterVal = [filterVal]
          }
          filterVal.forEach((val) => {
            f.push(key + '=' + encodeURIComponent(val))
          })
        }
      }
      url += hasParam ? '&' : '?'
      url += f.join('&')
    }
    return this.getJson(url)
  }

  searchPublicBodies (term, filters) {
    return this.getJsonForUrl(this.config.url.searchPublicBody, term, filters)
  }

  listPublicBodies (term, filters) {
    return this.getJsonForUrl(this.config.url.listPublicBodies, term, filters)
  }

  listJurisdictions (term, filters) {
    return this.getJsonForUrl(this.config.url.listJurisdictions, term, filters)
  }

  listCategories (term, filters) {
    return this.getJsonForUrl(this.config.url.listCategories, term, filters)
  }

  listClassifications (term, filters) {
    return this.getJsonForUrl(this.config.url.listClassifications, term, filters)
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
