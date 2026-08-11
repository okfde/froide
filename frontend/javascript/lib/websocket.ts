/*
 * Websocket room implementation
 * new Room('/ws/some-room/').connect().on('event', (data) => console.log(data))
 *
 */

const HEARTBEAT_SECONDS = 30
const RETRY_SECONDS = 3

type AppData = Record<string, unknown>
type Callback = (data: AppData) => void

type CallbackMapping = Map<string, Callback[]>

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
  private callbacks: CallbackMapping
  private queue: EventData[]
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
    this.callbacks = new Map()
    this.queue = []

    this.connect = this.connect.bind(this)
  }

  connect(): this {
    let prot = 'ws'
    if (document.location.protocol === 'https:') {
      prot = 'wss'
    }
    this.socket = new WebSocket(`${prot}://${window.location.host}${this.url}`)
    this.clearRetry()

    this.socket.addEventListener('open', () => {
      this.socketClosed = false
      this.setupHeartbeat()
      this.queue.forEach((d) => {
        if (this.socket != null) {
          this.socket.send(JSON.stringify(d))
        }
      })
      this.queue = []
      // provide this binding to onunload; keep handle around for removing in onclose
      this.onUnloadHandler = () => this.onunload()
      window.addEventListener('beforeunload', this.onUnloadHandler)
    })
    this.socket.addEventListener('message', (e) => {
      const data = JSON.parse(e.data) as EventData
      this.trigger(data.type, data)
    })
    this.socket.addEventListener('error', (e) => {
      console.info('websocket error', e)
    })
    this.socket.addEventListener('close', () => {
      this.cleanup()
      if (!this.socketClosed) {
        console.info('Socket closed unexpectedly. Retrying...')
        this.setupRetry()
      }
    })
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
    const cbs = this.callbacks.get(event)
    if (cbs) {
      cbs.push(callback)
    } else {
      this.callbacks.set(event, [callback])
    }
    return this
  }

  off(event: string, callback: Callback): this {
    let cbs = this.callbacks.get(event) || []
    cbs = cbs.filter((cb) => cb !== callback)
    if (cbs.length === 0) {
      this.callbacks.delete(event)
    } else {
      this.callbacks.set(event, cbs)
    }
    return this
  }

  trigger(event: string, data: AppData): void {
    const cbs = this.callbacks.get(event)
    if (cbs === undefined) {
      return
    } else {
      cbs.forEach((cb) => {
        cb(data)
      })
    }
  }

  cleanup(): void {
    if (this.onUnloadHandler) {
      window.removeEventListener('beforeunload', this.onUnloadHandler)
    }
    this.clearHeartbeat()
  }

  close(): void {
    this.cleanup()
    this.clearRetry()
    this.closeSocket()
  }

  closeSocket(): void {
    this.socketClosed = true
    if (this.queue.length > 0) {
      console.warn('Unsend messages in queue when closing socket')
    }
    if (this.socket != null) {
      this.socket.close()
      this.socket = null
    }
  }

  setupHeartbeat(): void {
    this.heartBeatInterval = window.setInterval(() => {
      if (this.socket != null && this.socket.readyState === 1) {
        this.socket.send(JSON.stringify({ type: 'heartbeat' }))
      } else {
        this.clearHeartbeat()
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
