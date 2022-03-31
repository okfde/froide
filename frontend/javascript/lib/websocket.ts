/*
 * Websocket room implementation
 * new Room('/ws/some-room/').connect().on('event', (data) => console.log(data))
 *
*/

const HEARTBEAT_SECONDS = 30
const RETRY_SECONDS = 3

interface CallbackMapping {
  [key: string]: Function[]
}

interface EventData {
  type: string
  [key: string]: any
}

class Room {
  public url: string
  private socket: WebSocket | null = null
  private retryInterval: number | null = null
  private heartBeatInterval: number | null = null
  private closed = true
  private callbacks: CallbackMapping = {}
  private queue: EventData[] = []
  private readonly heartbeatSeconds: number
  private readonly retrySeconds: number

  constructor (url: string, heartbeatSeconds = HEARTBEAT_SECONDS, retrySeconds = RETRY_SECONDS) {
    this.url = url
    this.heartbeatSeconds = heartbeatSeconds
    this.retrySeconds = retrySeconds

    this.connect = this.connect.bind(this)
  }

  connect () {
    let prot = 'ws'
    if (document.location.protocol === 'https:') {
      prot = 'wss'
    }
    this.socket = new WebSocket(`${prot}://${window.location.host}${this.url}`)
    this.clearRetry()

    this.socket.onopen = () => {
      this.closed = false
      this.setupHeartbeat()
      this.queue.forEach(d => {
        if (this.socket != null) {
          this.socket.send(JSON.stringify(d))
        }
      })
      window.addEventListener('beforeunload', this.onunload)
      this.queue = []
    }
    this.socket.onmessage = (e) => {
      const data = JSON.parse(e.data) as EventData
      this.trigger(data.type, data)
    }
    this.socket.onerror = (e) => {
      console.error(e)
    }
    this.socket.onclose = () => {
      this.clearHeartbeat()
      window.removeEventListener('beforeunload', this.onunload)
      if (!this.closed) {
        console.error('Socket closed unexpectedly. Retrying...')
        this.setupRetry()
      }
    }
    return this
  }

  onunload () {
    if (!this.closed) {
      this.close()
    }
  }

  send (data: EventData) {
    if ((this.socket != null) && this.socket.readyState === 1) {
      this.socket.send(JSON.stringify(data))
    } else {
      this.queue.push(data)
    }
  }

  on (event: string, callback: Function) {
    this.callbacks[event] = this.callbacks[event] || []
    this.callbacks[event].push(callback)
    return this
  }

  off (event: string, callback: Function) {
    this.callbacks[event] = this.callbacks[event] || []
    this.callbacks[event] = this.callbacks[event].filter((cb) => cb !== callback)
    return this
  }

  trigger (event: string, data: Object) {
    if (!this.callbacks[event]) {
      return
    }
    this.callbacks[event].forEach((cb) => {
      cb(data)
    })
  }

  close () {
    this.closed = true
    if (this.socket != null) {
      this.socket.close()
    }
  }

  setupHeartbeat () {
    this.heartBeatInterval = window.setInterval(() => {
      if ((this.socket != null) && this.socket.readyState === 1) {
        this.socket.send(JSON.stringify({ type: 'heartbeat' }))
      } else {
        if (this.heartBeatInterval) {
          window.clearInterval(this.heartBeatInterval)
          this.heartBeatInterval = null
        }
      }
    }, this.heartbeatSeconds * 1000)
  }

  clearHeartbeat () {
    if (this.heartBeatInterval) {
      window.clearInterval(this.heartBeatInterval)
    }
    this.heartBeatInterval = null
  }

  setupRetry () {
    if (!this.retryInterval) {
      this.retryInterval = window.setInterval(this.connect, this.retrySeconds * 1000)
    }
  }

  clearRetry () {
    if (this.retryInterval) {
      window.clearInterval(this.retryInterval)
      this.retryInterval = null
    }
  }
}

export default Room
