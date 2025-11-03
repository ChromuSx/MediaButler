class WebSocketService {
  constructor() {
    this.ws = null;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = Infinity; // Infinite reconnection attempts
    this.baseReconnectDelay = 1000; // Start with 1 second
    this.maxReconnectDelay = 30000; // Max 30 seconds
    this.pingInterval = null;
    this.pingIntervalTime = 30000; // Send ping every 30 seconds
  }

  connect() {
    // Use relative URL for WebSocket in development (Vite proxy will handle it)
    const WS_URL = import.meta.env.VITE_WS_URL || (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host;
    const wsUrl = `${WS_URL}/ws/updates`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.startPingInterval();
        this.emit('connected', {});
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          // Handle pong response (keep-alive acknowledgment)
          if (message.type === 'pong') {
            // Connection is alive, no action needed
            return;
          }
          this.emit(message.type, message.data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.emit('error', error);
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.stopPingInterval();
        this.emit('disconnected', {});
        this.attemptReconnect();
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;

      // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (max)
      const delay = Math.min(
        this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
        this.maxReconnectDelay
      );

      console.log(`Reconnecting... Attempt ${this.reconnectAttempts} (waiting ${delay}ms)`);
      setTimeout(() => this.connect(), delay);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  disconnect() {
    this.stopPingInterval();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  startPingInterval() {
    // Clear any existing interval
    this.stopPingInterval();

    // Send ping every 30 seconds to keep connection alive
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send('ping', {});
      }
    }, this.pingIntervalTime);
  }

  stopPingInterval() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  send(type, data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
    } else {
      console.warn('WebSocket is not connected');
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach((callback) => callback(data));
    }
  }
}

// Create singleton instance
const wsService = new WebSocketService();

export default wsService;
