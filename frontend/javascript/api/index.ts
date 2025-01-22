import { client } from './gen/services.gen'

const token = document.cookie.match(/csrftoken=([^;]+)/)?.[1]

client.interceptors.request.use((request) => {
  request.headers.set('X-CSRFToken', token!)
  return request
})

export * from './gen/schemas.gen'
export * from './gen/services.gen'
export * from './gen/types.gen'
