import { client } from './gen/services.gen'

export const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1]

const SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS']

client.interceptors.request.use((request) => {
  if (!SAFE_METHODS.includes(request.method)) {
    request.headers.set('X-CSRFToken', csrfToken!)
  }
  return request
})

export * from './gen/schemas.gen'
export * from './gen/services.gen'
export * from './gen/types.gen'
