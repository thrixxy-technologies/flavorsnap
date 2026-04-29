import { useState, useEffect, useCallback, useRef } from 'react';
import { Notification, NotificationType, NotificationPriority, NotificationPreferences } from '../components/NotificationSystem';

export interface UseNotificationsReturn {
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearAllNotifications: () => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  preferences: NotificationPreferences;
  updatePreferences: (preferences: Partial<NotificationPreferences>) => void;
  requestPermission: () => Promise<boolean>;
  isSupported: boolean;
  unreadCount: number;
  subscribeToPush: () => Promise<boolean>;
  unsubscribeFromPush: () => Promise<void>;
}

const DEFAULT_PREFERENCES: NotificationPreferences = {
  enabled: true,
  sound: true,
  vibration: true,
  doNotDisturb: false,
  doNotDisturbSchedule: {
    enabled: false,
    start: '22:00',
    end: '08:00'
  },
  types: {
    success: true,
    error: true,
    warning: true,
    info: true,
    classification: true
  },
  priorities: {
    low: true,
    medium: true,
    high: true,
    urgent: true
  }
};

export const useNotifications = (): UseNotificationsReturn => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [preferences, setPreferences] = useState<NotificationPreferences>(DEFAULT_PREFERENCES);
  const [isSupported, setIsSupported] = useState(false);
  const subscriptionRef = useRef<PushSubscription | null>(null);

  useEffect(() => {
    const supported = 'Notification' in window && 'serviceWorker' in navigator && 'PushManager' in window;
    setIsSupported(supported);

    const savedPreferences = localStorage.getItem('notification-preferences');
    if (savedPreferences) {
      try {
        setPreferences({ ...DEFAULT_PREFERENCES, ...JSON.parse(savedPreferences) });
      } catch (error) {
        console.error('Failed to load notification preferences:', error);
      }
    }

    const savedNotifications = localStorage.getItem('notifications');
    if (savedNotifications) {
      try {
        const parsed = JSON.parse(savedNotifications);
        setNotifications(parsed.map((n: any) => ({
          ...n,
          timestamp: new Date(n.timestamp)
        })));
      } catch (error) {
        console.error('Failed to load notifications:', error);
      }
    }

    if (supported) {
      navigator.serviceWorker.ready.then((registration) => {
        return registration.pushManager.getSubscription();
      }).then((subscription) => {
        subscriptionRef.current = subscription;
      });
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('notification-preferences', JSON.stringify(preferences));
  }, [preferences]);

  useEffect(() => {
    const notificationsToSave = notifications.map(n => ({
      ...n,
      timestamp: n.timestamp.toISOString()
    }));
    localStorage.setItem('notifications', JSON.stringify(notificationsToSave));
  }, [notifications]);

  const isInDoNotDisturbPeriod = useCallback(() => {
    if (!preferences.doNotDisturb || !preferences.doNotDisturbSchedule.enabled) {
      return false;
    }

    const now = new Date();
    const currentTime = now.getHours() * 60 + now.getMinutes();
    const [startHour, startMin] = preferences.doNotDisturbSchedule.start.split(':').map(Number);
    const [endHour, endMin] = preferences.doNotDisturbSchedule.end.split(':').map(Number);
    const startTime = startHour * 60 + startMin;
    const endTime = endHour * 60 + endMin;

    if (startTime <= endTime) {
      return currentTime >= startTime && currentTime <= endTime;
    } else {
      return currentTime >= startTime || currentTime <= endTime;
    }
  }, [preferences]);

  const canShowNotification = useCallback((notification: Notification) => {
    if (!preferences.enabled) return false;
    if (isInDoNotDisturbPeriod() && notification.priority !== 'urgent') return false;
    if (!preferences.types[notification.type]) return false;
    if (!preferences.priorities[notification.priority]) return false;
    return true;
  }, [preferences, isInDoNotDisturbPeriod]);

  const playSound = useCallback((soundType?: string) => {
    if (!preferences.sound) return;
    
    try {
      const audio = new Audio();
      switch (soundType || 'default') {
        case 'success':
          audio.src = '/sounds/success.mp3';
          break;
        case 'error':
          audio.src = '/sounds/error.mp3';
          break;
        case 'classification':
          audio.src = '/sounds/classification.mp3';
          break;
        default:
          audio.src = '/sounds/notification.mp3';
      }
      audio.play().catch(() => {});
    } catch (error) {
      console.error('Failed to play notification sound:', error);
    }
  }, [preferences.sound]);

  const triggerVibration = useCallback(() => {
    if (!preferences.vibration || !('vibrate' in navigator)) return;
    
    try {
      navigator.vibrate([200, 100, 200]);
    } catch (error) {
      console.error('Failed to trigger vibration:', error);
    }
  }, [preferences.vibration]);

  const showBrowserNotification = useCallback((notification: Notification) => {
    if (!('Notification' in window) || Notification.permission !== 'granted') return;

    const browserNotification = new Notification(notification.title, {
      body: notification.message,
      icon: '/icons/icon-192x192.png',
      badge: '/icons/icon-96x96.png',
      tag: notification.id,
      requireInteraction: notification.persistent,
      silent: !preferences.sound
    });

    if (notification.actions) {
      browserNotification.onclick = () => {
        notification.actions[0]?.action();
        browserNotification.close();
      };
    }

    setTimeout(() => {
      browserNotification.close();
    }, notification.duration || 5000);
  }, [preferences.sound]);

  const addNotification = useCallback((notificationData: Omit<Notification, 'id' | 'timestamp'>) => {
    const notification: Notification = {
      ...notificationData,
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date(),
      read: false
    };

    if (!canShowNotification(notification)) return;

    setNotifications(prev => [notification, ...prev]);

    if (!notificationData.persistent) {
      playSound(notificationData.sound);
      triggerVibration();
      showBrowserNotification(notification);

      setTimeout(() => {
        removeNotification(notification.id);
      }, notificationData.duration || 5000);
    }
  }, [canShowNotification, playSound, triggerVibration, showBrowserNotification]);

  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  const clearAllNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  const markAsRead = useCallback((id: string) => {
    setNotifications(prev => 
      prev.map(n => n.id === id ? { ...n, read: true } : n)
    );
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications(prev => 
      prev.map(n => ({ ...n, read: true }))
    );
  }, []);

  const updatePreferences = useCallback((newPreferences: Partial<NotificationPreferences>) => {
    setPreferences(prev => ({ ...prev, ...newPreferences }));
  }, []);

  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (!('Notification' in window)) return false;

    if (Notification.permission === 'default') {
      const permission = await Notification.requestPermission();
      return permission === 'granted';
    }

    return Notification.permission === 'granted';
  }, []);

  const subscribeToPush = useCallback(async (): Promise<boolean> => {
    if (!isSupported) return false;

    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY
      });

      subscriptionRef.current = subscription;

      await fetch('/api/push/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(subscription)
      });

      return true;
    } catch (error) {
      console.error('Failed to subscribe to push notifications:', error);
      return false;
    }
  }, [isSupported]);

  const unsubscribeFromPush = useCallback(async (): Promise<void> => {
    if (subscriptionRef.current) {
      try {
        await subscriptionRef.current.unsubscribe();
        subscriptionRef.current = null;

        await fetch('/api/push/unsubscribe', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          }
        });
      } catch (error) {
        console.error('Failed to unsubscribe from push notifications:', error);
      }
    }
  }, []);

  const unreadCount = notifications.filter(n => !n.read).length;

  useEffect(() => {
    const handlePushMessage = (event: MessageEvent) => {
      if (event.data?.type === 'PUSH_NOTIFICATION') {
        addNotification(event.data.payload);
      }
    };

    navigator.serviceWorker?.addEventListener('message', handlePushMessage);

    return () => {
      navigator.serviceWorker?.removeEventListener('message', handlePushMessage);
    };
  }, [addNotification]);

  return {
    notifications,
    addNotification,
    removeNotification,
    clearAllNotifications,
    markAsRead,
    markAllAsRead,
    preferences,
    updatePreferences,
    requestPermission,
    isSupported,
    unreadCount,
    subscribeToPush,
    unsubscribeFromPush
  };
};

export default useNotifications;
