class FroideAPI {
  constructor(config) {
    this.config = config
  }

  getJson(url) {
    return new Promise((resolve, reject) => {
      const request = new window.XMLHttpRequest()
      request.open('GET', url, true)
      request.onload = function() {
        if (request.status >= 400) {
          try {
            return reject(JSON.parse(request.responseText))
          } catch (e) {
            return reject(request.responseText)
          }
        }
        resolve(JSON.parse(request.responseText))
      }
      request.onerror = function() {
        reject(request.statusText)
      }

      request.send()
    })
  }

  getObjects(promise) {
    return new Promise((resolve, reject) => {
      promise
        .then((data) => {
          return resolve(data.objects)
        })
        .catch((e) => reject(e))
    })
  }

  getJsonObjects(url) {
    return new Promise((resolve, reject) => {
      this.getJsonForUrl(url)
        .then((data) => resolve(data.objects))
        .catch((e) => reject(e))
    })
  }

  getPublicBody(id) {
    const url = this.config.url.getPublicBody.replace(/\/0\//, `/${id}/`)
    return this.getJsonForUrl(url)
  }

  autocompletePublicBody(term) {
    const query = encodeURIComponent(term)
    const url = this.config.url.autocompletePublicBody + '?query=' + query
    return this.getJsonObjects(url)
  }

  getUser() {
    return this.getJson(this.config.url.user)
  }

  getJsonForUrl(url, term, filters) {
    let hasParam = false
    if (term !== undefined && term) {
      hasParam = true
      url = url + '?q=' + encodeURIComponent(term)
    } else {
      hasParam = url.indexOf('?') !== -1
    }

    filters = filters || {}
    filters.language = document.documentElement.lang
    const f = []
    for (const key in filters) {
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
    return this.getJson(url)
  }

  searchPublicBodies(term, filters) {
    return this.getJsonForUrl(this.config.url.searchPublicBody, term, filters)
  }

  listPublicBodies(term, filters) {
    return this.getJsonForUrl(this.config.url.listPublicBodies, term, filters)
  }

  getLawsForPublicBodies(publicBodies, cachedLaws) {
    cachedLaws = cachedLaws || {}
    const lawIdMap = {}
    const lawIds = []
    publicBodies.forEach((pb) => {
      pb.laws.forEach((law) => {
        if (typeof law === 'string') {
          if (cachedLaws[law] !== undefined) {
            return
          }
          const parts = law.split('/')
          const lawId = parts[parts.length - 2]
          if (lawIdMap[lawId] === undefined) {
            lawIdMap[lawId] = true
            lawIds.push(lawId)
          }
        }
      })
    })
    if (lawIds.length === 0) {
      return Promise.resolve([])
    }
    return this.getJsonForUrl(this.config.url.listLaws, null, {
      id: lawIds.join(',')
    }).then((data) => data.objects)
  }

  listJurisdictions(term, filters) {
    return this.getJsonForUrl(this.config.url.listJurisdictions, term, filters)
  }

  listCategories(term, filters) {
    return this.getJsonForUrl(this.config.url.listCategories, term, filters)
  }

  listClassifications(term, filters) {
    return this.getJsonForUrl(
      this.config.url.listClassifications,
      term,
      filters
    )
  }

  listGeoregions(term, filters) {
    return this.getJsonForUrl(this.config.url.listGeoregions, term, filters)
  }

  searchFoiRequests(term) {
    const query = encodeURIComponent(term)
    const url = this.config.url.searchRequests + '?q=' + query
    return this.getJsonObjects(url)
  }
}

function postData(url = '', data = {}, csrfToken, method = 'POST') {
  return window
    .fetch(url, {
      method: method,
      cache: 'no-cache',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(data)
    })
    .then((response) => response.json())
}

function putData(url = '', data = {}, csrfToken) {
  return postData(url, data, csrfToken, 'PUT')
}

function getData(url = '', headers = {}) {
  headers = headers || {}
  return window
    .fetch(url, {
      method: 'GET',
      cache: 'no-cache',
      credentials: 'same-origin',
      headers: {
        Accept: 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        ...headers
      }
    })
    .then((response) => response.json())
}

function getAllData(url = '', headers = {}, result = [], progress = null) {
  return new Promise((resolve, reject) => {
    getData(url, headers).then((data) => {
      result = [...result, ...data.objects]
      if (data.meta.next) {
        if (progress) {
          progress(result)
        }
        getAllData(data.meta.next, headers, result).then(resolve).catch(reject)
      } else {
        resolve(result)
      }
    })
  })
}

function bustCache(url) {
  return window.fetch(url, {
    method: 'GET',
    cache: 'no-cache',
    credentials: 'same-origin',
    headers: {
      pragma: 'no-cache',
      'cache-control': 'no-cache'
    }
  })
}

export { FroideAPI, postData, putData, getData, getAllData, bustCache }
