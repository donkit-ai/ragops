import { useCallback, useEffect, useRef, useState } from 'react';
import { WebSocketMessage } from '../types/protocol';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface UseWebSocketOptions {
  onMessage: (message: WebSocketMessage) => void;
  onError?: (error: Event) => void;
  onClose?: () => void;
  onOpen?: () => void;
}

export function useWebSocket(sessionId: string | null, options: UseWebSocketOptions) {
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const disconnectTimeoutRef = useRef<number | null>(null);
  const optionsRef = useRef(options);
  const mountedRef = useRef(true);

  // Keep options ref updated
  useEffect(() => {
    optionsRef.current = options;
  }, [options]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (disconnectTimeoutRef.current) {
      clearTimeout(disconnectTimeoutRef.current);
      disconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus('disconnected');
  }, []);

  const connect = useCallback(() => {
    if (!sessionId) return;

    // Cancel any pending disconnect (handles React StrictMode remount)
    if (disconnectTimeoutRef.current) {
      clearTimeout(disconnectTimeoutRef.current);
      disconnectTimeoutRef.current = null;
    }

    // Prevent multiple connections
    if (wsRef.current) {
      const state = wsRef.current.readyState;
      if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) {
        return;
      }
    }

    setStatus('connecting');

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const ws = new WebSocket(`${protocol}//${host}/api/v1/ws/${sessionId}`);

    ws.onopen = () => {
      console.log('[useWebSocket] Connection opened');
      setStatus('connected');
      optionsRef.current.onOpen?.();
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage;
        console.log('[useWebSocket] Message received:', message);
        optionsRef.current.onMessage(message);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onerror = (event) => {
      setStatus('error');
      optionsRef.current.onError?.(event);
    };

    ws.onclose = () => {
      setStatus('disconnected');
      optionsRef.current.onClose?.();
      wsRef.current = null;
    };

    wsRef.current = ws;
  }, [sessionId]);

  const send = useCallback((message: { type: string; content?: string; [key: string]: unknown }) => {
    console.log('[useWebSocket] send called:', message);
    console.log('[useWebSocket] wsRef.current:', wsRef.current);
    console.log('[useWebSocket] readyState:', wsRef.current?.readyState);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('[useWebSocket] Sending message...');
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.log('[useWebSocket] Cannot send - socket not open');
    }
  }, []);

  const sendChat = useCallback((content: string, silent?: boolean) => {
    send({ type: 'chat', content, silent: silent ?? false });
  }, [send]);

  const sendCancel = useCallback(() => {
    send({ type: 'cancel' });
  }, [send]);

  const sendPing = useCallback(() => {
    send({ type: 'ping' });
  }, [send]);

  const sendInteractiveResponse = useCallback(
    (requestId: string, data: Record<string, unknown>) => {
      send({ type: 'interactive_response', request_id: requestId, ...data });
    },
    [send]
  );

  // Connect when sessionId changes
  useEffect(() => {
    mountedRef.current = true;

    if (sessionId) {
      connect();
    }

    return () => {
      mountedRef.current = false;
      // Delay disconnect to handle React StrictMode's unmount/remount cycle.
      // If the component remounts quickly (StrictMode), connect() will cancel this timeout.
      disconnectTimeoutRef.current = window.setTimeout(() => {
        if (!mountedRef.current) {
          disconnect();
        }
      }, 100);
    };
  }, [sessionId]); // Only depend on sessionId, not on connect/disconnect

  // Ping every 30 seconds to keep connection alive
  useEffect(() => {
    if (status !== 'connected') return;

    const interval = setInterval(() => {
      sendPing();
    }, 30000);

    return () => clearInterval(interval);
  }, [status, sendPing]);

  return {
    status,
    connect,
    disconnect,
    sendChat,
    sendCancel,
    sendPing,
    sendInteractiveResponse,
  };
}
