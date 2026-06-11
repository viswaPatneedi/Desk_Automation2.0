import { io } from 'socket.io-client';

const WS_URL = import.meta.env.VITE_WS_URL || 'http://localhost:5000';
const RECONNECT_INTERVAL = parseInt(import.meta.env.VITE_WS_RECONNECT_INTERVAL || '5000');
const MAX_RECONNECT_ATTEMPTS = parseInt(import.meta.env.VITE_WS_MAX_RECONNECT_ATTEMPTS || '10');

let socket = null;
let listeners = {};

export const initializeWebSocket = () => {
  if (socket && socket.connected) {
    return socket;
  }

  const token = localStorage.getItem('lrqa_auth_token');

  socket = io(WS_URL, {
    auth: {
      token,
    },
    reconnection: true,
    reconnectionDelay: RECONNECT_INTERVAL,
    reconnectionDelayMax: RECONNECT_INTERVAL * 2,
    reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
    transports: ['websocket', 'polling'],
  });

  // Connection events
  socket.on('connect', () => {
    console.log('WebSocket connected:', socket.id);
    broadcastEvent('ws:connected', { socketId: socket.id });
  });

  socket.on('disconnect', (reason) => {
    console.log('WebSocket disconnected:', reason);
    broadcastEvent('ws:disconnected', { reason });
  });

  socket.on('connect_error', (error) => {
    console.error('WebSocket connection error:', error);
    broadcastEvent('ws:error', { error: error.message });
  });

  // Server events
  socket.on('job:status_changed', (data) => {
    broadcastEvent('job:status_changed', data);
  });

  socket.on('device:status_changed', (data) => {
    broadcastEvent('device:status_changed', data);
  });

  socket.on('execution:started', (data) => {
    broadcastEvent('execution:started', data);
  });

  socket.on('execution:progress', (data) => {
    broadcastEvent('execution:progress', data);
  });

  socket.on('execution:completed', (data) => {
    broadcastEvent('execution:completed', data);
  });

  socket.on('execution:failed', (data) => {
    broadcastEvent('execution:failed', data);
  });

  socket.on('log:update', (data) => {
    broadcastEvent('log:update', data);
  });

  socket.on('notification', (data) => {
    broadcastEvent('notification', data);
  });

  return socket;
};

export const getWebSocket = () => {
  if (!socket) {
    return initializeWebSocket();
  }
  return socket;
};

export const isWebSocketConnected = () => {
  return socket?.connected || false;
};

// Event subscription system
export const subscribe = (event, callback) => {
  if (!listeners[event]) {
    listeners[event] = [];
  }
  listeners[event].push(callback);

  // Return unsubscribe function
  return () => {
    listeners[event] = listeners[event].filter(cb => cb !== callback);
  };
};

export const unsubscribe = (event, callback) => {
  if (listeners[event]) {
    listeners[event] = listeners[event].filter(cb => cb !== callback);
  }
};

const broadcastEvent = (event, data) => {
  if (listeners[event]) {
    listeners[event].forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error(`Error in listener for ${event}:`, error);
      }
    });
  }
};

// Emit functions
export const emitJobCreate = (jobData) => {
  if (socket?.connected) {
    socket.emit('job:create', jobData);
  }
};

export const emitJobCancel = (jobId) => {
  if (socket?.connected) {
    socket.emit('job:cancel', { id: jobId });
  }
};

export const emitDeviceAdd = (deviceData) => {
  if (socket?.connected) {
    socket.emit('device:add', deviceData);
  }
};

export const emitDeviceUpdate = (deviceId, data) => {
  if (socket?.connected) {
    socket.emit('device:update', { id: deviceId, ...data });
  }
};

export const emitSubscribeToJob = (jobId) => {
  if (socket?.connected) {
    socket.emit('subscribe:job', { jobId });
  }
};

export const emitUnsubscribeFromJob = (jobId) => {
  if (socket?.connected) {
    socket.emit('unsubscribe:job', { jobId });
  }
};

export const emitSubscribeToDevice = (deviceId) => {
  if (socket?.connected) {
    socket.emit('subscribe:device', { deviceId });
  }
};

export const emitUnsubscribeFromDevice = (deviceId) => {
  if (socket?.connected) {
    socket.emit('unsubscribe:device', { deviceId });
  }
};

export const disconnectWebSocket = () => {
  if (socket) {
    socket.disconnect();
    socket = null;
    listeners = {};
  }
};
