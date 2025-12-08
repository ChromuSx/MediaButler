import { useEffect, useState, useCallback, useRef } from 'react';
import wsService from '../services/websocket';

/**
 * Custom hook for WebSocket connection and event handling
 * @param {boolean} autoConnect - Automatically connect on mount (default: true)
 * @returns {Object} WebSocket state and methods
 */
export function useWebSocket(autoConnect = true) {
  const [isConnected, setIsConnected] = useState(false);
  const listenersRef = useRef(new Map());

  useEffect(() => {
    // Connection status handlers
    const handleConnected = () => setIsConnected(true);
    const handleDisconnected = () => setIsConnected(false);

    wsService.on('connected', handleConnected);
    wsService.on('disconnected', handleDisconnected);

    // Auto-connect if enabled
    if (autoConnect) {
      wsService.connect();
    }

    // Save current listeners for cleanup
    const currentListeners = listenersRef.current;

    // Cleanup on unmount
    return () => {
      wsService.off('connected', handleConnected);
      wsService.off('disconnected', handleDisconnected);

      // Remove all event listeners registered by this hook
      currentListeners.forEach((callback, event) => {
        wsService.off(event, callback);
      });
      currentListeners.clear();
    };
  }, [autoConnect]);

  /**
   * Subscribe to a WebSocket event
   * @param {string} event - Event name
   * @param {Function} callback - Callback function
   */
  const on = useCallback((event, callback) => {
    wsService.on(event, callback);
    listenersRef.current.set(event, callback);
  }, []);

  /**
   * Unsubscribe from a WebSocket event
   * @param {string} event - Event name
   * @param {Function} callback - Callback function
   */
  const off = useCallback((event, callback) => {
    wsService.off(event, callback);
    listenersRef.current.delete(event);
  }, []);

  /**
   * Send a message through WebSocket
   * @param {string} type - Message type
   * @param {Object} data - Message data
   */
  const send = useCallback((type, data) => {
    wsService.send(type, data);
  }, []);

  /**
   * Manually connect to WebSocket
   */
  const connect = useCallback(() => {
    wsService.connect();
  }, []);

  /**
   * Manually disconnect from WebSocket
   */
  const disconnect = useCallback(() => {
    wsService.disconnect();
  }, []);

  return {
    isConnected,
    on,
    off,
    send,
    connect,
    disconnect
  };
}

/**
 * Hook for listening to specific WebSocket events
 * @param {string} eventType - Event type to listen for
 * @param {Function} callback - Callback function
 * @param {Array} deps - Dependency array for callback
 */
export function useWebSocketEvent(eventType, callback, deps = []) {
  const { on, off } = useWebSocket(true);

  useEffect(() => {
    const handler = (data) => {
      callback(data);
    };

    on(eventType, handler);

    return () => {
      off(eventType, handler);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventType, on, off, callback, ...deps]);
}

/**
 * Hook for download progress updates
 * @param {Function} onProgress - Callback for progress updates
 * @param {Function} onCompleted - Callback for completed downloads
 * @param {Function} onFailed - Callback for failed downloads
 * @param {Function} onStarted - Callback for started downloads
 */
export function useDownloadUpdates({
  onProgress,
  onCompleted,
  onFailed,
  onStarted
} = {}) {
  useWebSocketEvent('download_progress', (data) => {
    if (onProgress) onProgress(data);
  }, [onProgress]);

  useWebSocketEvent('download_completed', (data) => {
    if (onCompleted) onCompleted(data);
  }, [onCompleted]);

  useWebSocketEvent('download_failed', (data) => {
    if (onFailed) onFailed(data);
  }, [onFailed]);

  useWebSocketEvent('download_started', (data) => {
    if (onStarted) onStarted(data);
  }, [onStarted]);
}

/**
 * Hook for stats updates
 * @param {Function} callback - Callback for stats updates
 */
export function useStatsUpdates(callback) {
  useWebSocketEvent('stats_update', callback, [callback]);
}

/**
 * Hook for user management updates
 * @param {Function} onUserAdded - Callback for new users
 * @param {Function} onUserRemoved - Callback for removed users
 */
export function useUserUpdates({ onUserAdded, onUserRemoved } = {}) {
  useWebSocketEvent('user_added', (data) => {
    if (onUserAdded) onUserAdded(data);
  }, [onUserAdded]);

  useWebSocketEvent('user_removed', (data) => {
    if (onUserRemoved) onUserRemoved(data);
  }, [onUserRemoved]);
}

/**
 * Hook for space warnings
 * @param {Function} callback - Callback for space warnings
 */
export function useSpaceWarnings(callback) {
  useWebSocketEvent('space_warning', callback, [callback]);
}

export default useWebSocket;
