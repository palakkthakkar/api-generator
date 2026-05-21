import { useState, useEffect, useRef, useCallback } from 'react';

interface WSMessage {
  channel: string;
  data: any;
}

export function useWebSocket(url: string) {
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    // Don't reconnect if unmounted
    if (!mountedRef.current) return;

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        if (mountedRef.current) {
          setIsConnected(true);
          console.log('[WS] Connected to', url);
        }
      };

      ws.onclose = (event) => {
        if (mountedRef.current) {
          setIsConnected(false);
          console.log('[WS] Disconnected. Reconnecting in 3s...', event.reason);
          // Auto-reconnect
          reconnectTimeoutRef.current = setTimeout(connect, 3000);
        }
      };

      ws.onerror = (error) => {
        console.error('[WS] Error:', error);
      };

      ws.onmessage = (event) => {
        try {
          const parsed: WSMessage = JSON.parse(event.data);
          if (mountedRef.current) {
            setLastMessage(parsed);
          }
        } catch (err) {
          console.warn('[WS] Failed to parse message:', err);
        }
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('[WS] Failed to create connection:', err);
      if (mountedRef.current) {
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      }
    }
  }, [url]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { lastMessage, isConnected };
}
