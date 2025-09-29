/*
 * Websocket room implementation
 * new Room('/ws/some-room/').connect().on('event', (data) => console.log(data))
 *
 */

const HEARTBEAT_SECONDS = 30
const RETRY_SECONDS = 3

type AppData = Record<string, unknown>
type Callback = (data: AppData) => void

type CallbackMapping = Record<string, Callback[]>

interface EventData {
  type: string
  [key: string]: any
}

class Room {
  public url: string
  private socket: WebSocket | null = null
  private retryInterval: number | null = null
  private heartBeatInterval: number | null = null
  private socketClosed = true
  private callbacks: CallbackMapping = {}
  private queue: EventData[] = []
  private onUnloadHandler: EventListener | null = null
  private readonly heartbeatSeconds: number
  private readonly retrySeconds: number

  constructor(
    url: string,
    heartbeatSeconds = HEARTBEAT_SECONDS,
    retrySeconds = RETRY_SECONDS
  ) {
    this.url = url
    this.heartbeatSeconds = heartbeatSeconds
    this.retrySeconds = retrySeconds

    this.connect = this.connect.bind(this)
  }

  connect(): this {
    let prot = 'ws'
    if (document.location.protocol === 'https:') {
      prot = 'wss'
    }
    this.socket = new WebSocket(`${prot}://${window.location.host}${this.url}`)
    this.clearRetry()

    this.socket.onopen = () => {
      this.socketClosed = false
      this.setupHeartbeat()
      this.queue.forEach((d) => {
        if (this.socket != null) {
          this.socket.send(JSON.stringify(d))
        }
      })
      // provide this binding to onunload; keep handle around for removing in onclose
      this.onUnloadHandler = () => this.onunload()
      window.addEventListener('beforeunload', this.onUnloadHandler)
      this.queue = []
    }
    this.socket.onmessage = (e) => {
      const data = JSON.parse(e.data) as EventData
      this.trigger(data.type, data)
    }
    this.socket.onerror = (e) => {
      console.info('websocket error', e)
    }
    this.socket.onclose = () => {
      this.clearHeartbeat()
      window.removeEventListener('beforeunload', this.onUnloadHandler!)
      if (!this.socketClosed) {
        console.info('Socket closed unexpectedly. Retrying...')
        this.setupRetry()
      }
    }
    return this
  }

  onunload(): void {
    if (!this.socketClosed) {
      this.closeSocket()
    }
  }

  send(data: EventData): void {
    if (this.socket != null && this.socket.readyState === 1) {
      this.socket.send(JSON.stringify(data))
    } else {
      this.queue.push(data)
    }
  }

  on(event: string, callback: Callback): this {
    this.callbacks[event] = this.callbacks[event] || []
    this.callbacks[event].push(callback)
    return this
  }

  off(event: string, callback: Callback): this {
    this.callbacks[event] = this.callbacks[event] || []
    this.callbacks[event] = this.callbacks[event].filter(
      (cb) => cb !== callback
    )
    return this
  }

  trigger(event: string, data: AppData): void {
    if (!this.callbacks[event]) {
      return
    }
    this.callbacks[event].forEach((cb) => {
      cb(data)
    })
  }

  closeSocket(): void {
    this.socketClosed = true
    if (this.socket != null) {
      this.socket.close()
    }
  }

  setupHeartbeat(): void {
    this.heartBeatInterval = window.setInterval(() => {
      if (this.socket != null && this.socket.readyState === 1) {
        this.socket.send(JSON.stringify({ type: 'heartbeat' }))
      } else {
        if (this.heartBeatInterval) {
          window.clearInterval(this.heartBeatInterval)
          this.heartBeatInterval = null
        }
      }
    }, this.heartbeatSeconds * 1000)
  }

  clearHeartbeat(): void {
    if (this.heartBeatInterval) {
      window.clearInterval(this.heartBeatInterval)
    }
    this.heartBeatInterval = null
  }

  setupRetry(): void {
    if (!this.retryInterval) {
      this.retryInterval = window.setInterval(
        this.connect,
        this.retrySeconds * 1000
      )
    }
  }

  clearRetry(): void {
    if (this.retryInterval) {
      window.clearInterval(this.retryInterval)
      this.retryInterval = null
    }
  }
}

export default Room
