import { WsMessage } from '../types';

type MessageCallback = (data: WsMessage) => void;

class WebSocketClient {
  private socket: WebSocket | null = null;
  private listeners: Set<MessageCallback> = new Set();
  private reconnectInterval = 3000;
  private isExplicitlyClosed = false;

  public connect() {
    this.isExplicitlyClosed = false;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/live`;

    console.log(`[WebSocket] Connecting to ${wsUrl}...`);
    try {
      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        console.log('[WebSocket] Live stream connected.');
      };

      this.socket.onmessage = (event) => {
        try {
          const parsed: WsMessage = JSON.parse(event.data);
          this.listeners.forEach((callback) => callback(parsed));
        } catch (e) {
          console.warn('[WebSocket] Received non-JSON message:', event.data);
        }
      };

      this.socket.onclose = () => {
        console.log('[WebSocket] Connection closed.');
        if (!this.isExplicitlyClosed) {
          setTimeout(() => this.connect(), this.reconnectInterval);
        }
      };

      this.socket.onerror = (err) => {
        console.error('[WebSocket] Error:', err);
        this.socket?.close();
      };
    } catch (err) {
      console.error('[WebSocket] Connection initiation error:', err);
      if (!this.isExplicitlyClosed) {
        setTimeout(() => this.connect(), this.reconnectInterval);
      }
    }
  }

  public subscribe(callback: MessageCallback) {
    this.listeners.add(callback);
    return () => {
      this.listeners.delete(callback);
    };
  }

  public disconnect() {
    this.isExplicitlyClosed = true;
    if (this.socket) {
      this.socket.close();
    }
  }
}

export const wsClient = new WebSocketClient();
