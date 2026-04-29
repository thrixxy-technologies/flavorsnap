import React, { useState, useEffect, useCallback } from 'react';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle, Bell, BellOff, Search, Settings, Trash2, Volume2, Vibrate } from 'lucide-react';

export type NotificationType = 'success' | 'error' | 'warning' | 'info' | 'classification';

export type NotificationPriority = 'low' | 'medium' | 'high' | 'urgent';

export interface NotificationAction {
  id: string;
  label: string;
  action: () => void;
  primary?: boolean;
}

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: Date;
  priority: NotificationPriority;
  duration?: number;
  actions?: NotificationAction[];
  persistent?: boolean;
  read?: boolean;
  sound?: string;
  vibration?: boolean;
}

export interface NotificationPreferences {
  enabled: boolean;
  sound: boolean;
  vibration: boolean;
  doNotDisturb: boolean;
  doNotDisturbSchedule: {
    enabled: boolean;
    start: string;
    end: string;
  };
  types: {
    [key in NotificationType]: boolean;
  };
  priorities: {
    [key in NotificationPriority]: boolean;
  };
}

interface NotificationSystemProps {
  className?: string;
}

const NotificationSystem: React.FC<NotificationSystemProps> = ({ className = '' }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [showNotificationCenter, setShowNotificationCenter] = useState(false);
  const [preferences, setPreferences] = useState<NotificationPreferences>({
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
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [showPreferences, setShowPreferences] = useState(false);

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
  }, [preferences.sound]);

  const triggerVibration = useCallback(() => {
    if (!preferences.vibration || !('vibrate' in navigator)) return;
    
    navigator.vibrate([200, 100, 200]);
  }, [preferences.vibration]);

  const addNotification = useCallback((notification: Omit<Notification, 'id' | 'timestamp'>) => {
    const newNotification: Notification = {
      ...notification,
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date(),
      read: false
    };

    if (!canShowNotification(newNotification)) return;

    setNotifications(prev => [newNotification, ...prev]);

    if (!newNotification.persistent) {
      playSound(newNotification.sound);
      triggerVibration();

      setTimeout(() => {
        removeNotification(newNotification.id);
      }, newNotification.duration || 5000);
    }
  }, [canShowNotification, playSound, triggerVibration]);

  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  const markAsRead = useCallback((id: string) => {
    setNotifications(prev => 
      prev.map(n => n.id === id ? { ...n, read: true } : n)
    );
  }, []);

  const clearAllNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  const getNotificationIcon = (type: NotificationType) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      case 'info':
        return <Info className="w-5 h-5 text-blue-500" />;
      case 'classification':
        return <CheckCircle className="w-5 h-5 text-purple-500" />;
      default:
        return <Info className="w-5 h-5 text-gray-500" />;
    }
  };

  const getNotificationColor = (type: NotificationType) => {
    switch (type) {
      case 'success':
        return 'border-green-200 bg-green-50';
      case 'error':
        return 'border-red-200 bg-red-50';
      case 'warning':
        return 'border-yellow-200 bg-yellow-50';
      case 'info':
        return 'border-blue-200 bg-blue-50';
      case 'classification':
        return 'border-purple-200 bg-purple-50';
      default:
        return 'border-gray-200 bg-gray-50';
    }
  };

  const filteredNotifications = notifications.filter(n =>
    n.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    n.message.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const unreadCount = notifications.filter(n => !n.read).length;

  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  useEffect(() => {
    (window as any).addNotification = addNotification;
    (window as any).removeNotification = removeNotification;
    
    return () => {
      delete (window as any).addNotification;
      delete (window as any).removeNotification;
    };
  }, [addNotification, removeNotification]);

  return (
    <>
      <div className={`fixed top-4 right-4 z-50 space-y-2 ${className}`}>
        {notifications.slice(0, 5).map(notification => (
          <div
            key={notification.id}
            className={`max-w-sm p-4 rounded-lg border shadow-lg transition-all duration-300 transform animate-in slide-in-from-right ${getNotificationColor(notification.type)}`}
          >
            <div className="flex items-start gap-3">
              {getNotificationIcon(notification.type)}
              <div className="flex-1 min-w-0">
                <h4 className="font-semibold text-gray-900 truncate">{notification.title}</h4>
                <p className="text-sm text-gray-600 mt-1">{notification.message}</p>
                {notification.actions && (
                  <div className="flex gap-2 mt-3">
                    {notification.actions.map(action => (
                      <button
                        key={action.id}
                        onClick={() => {
                          action.action();
                          removeNotification(notification.id);
                        }}
                        className={`px-3 py-1 text-xs rounded ${
                          action.primary
                            ? 'bg-blue-500 text-white hover:bg-blue-600'
                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        }`}
                      >
                        {action.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <button
                onClick={() => removeNotification(notification.id)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="fixed bottom-4 right-4 z-40">
        <button
          onClick={() => setShowNotificationCenter(!showNotificationCenter)}
          className="relative p-3 bg-white rounded-full shadow-lg border border-gray-200 hover:bg-gray-50 transition-colors"
        >
          {preferences.doNotDisturb ? (
            <BellOff className="w-6 h-6 text-gray-400" />
          ) : (
            <Bell className="w-6 h-6 text-gray-700" />
          )}
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 w-6 h-6 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
              {unreadCount}
            </span>
          )}
        </button>
      </div>

      {showNotificationCenter && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold">Notifications</h2>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowPreferences(!showPreferences)}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <Settings className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => setShowNotificationCenter(false)}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search notifications..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <button
                  onClick={clearAllNotifications}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="overflow-y-auto max-h-96">
              {showPreferences ? (
                <NotificationPreferences
                  preferences={preferences}
                  setPreferences={setPreferences}
                />
              ) : (
                <div className="p-4 space-y-2">
                  {filteredNotifications.length === 0 ? (
                    <p className="text-center text-gray-500 py-8">No notifications</p>
                  ) : (
                    filteredNotifications.map(notification => (
                      <div
                        key={notification.id}
                        className={`p-4 rounded-lg border ${getNotificationColor(notification.type)} ${!notification.read ? 'font-semibold' : ''}`}
                        onClick={() => markAsRead(notification.id)}
                      >
                        <div className="flex items-start gap-3">
                          {getNotificationIcon(notification.type)}
                          <div className="flex-1">
                            <h4 className="font-medium">{notification.title}</h4>
                            <p className="text-sm text-gray-600 mt-1">{notification.message}</p>
                            <p className="text-xs text-gray-400 mt-2">
                              {notification.timestamp.toLocaleString()}
                            </p>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              removeNotification(notification.id);
                            }}
                            className="text-gray-400 hover:text-gray-600"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

const NotificationPreferences: React.FC<{
  preferences: NotificationPreferences;
  setPreferences: (preferences: NotificationPreferences) => void;
}> = ({ preferences, setPreferences }) => {
  const updatePreference = (key: keyof NotificationPreferences, value: any) => {
    setPreferences({ ...preferences, [key]: value });
  };

  const updateTypePreference = (type: NotificationType, enabled: boolean) => {
    setPreferences({
      ...preferences,
      types: { ...preferences.types, [type]: enabled }
    });
  };

  const updatePriorityPreference = (priority: NotificationPriority, enabled: boolean) => {
    setPreferences({
      ...preferences,
      priorities: { ...preferences.priorities, [priority]: enabled }
    });
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-4">General Settings</h3>
        <div className="space-y-3">
          <label className="flex items-center justify-between">
            <span>Enable Notifications</span>
            <input
              type="checkbox"
              checked={preferences.enabled}
              onChange={(e) => updatePreference('enabled', e.target.checked)}
              className="w-4 h-4"
            />
          </label>
          <label className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Volume2 className="w-4 h-4" />
              Sound
            </span>
            <input
              type="checkbox"
              checked={preferences.sound}
              onChange={(e) => updatePreference('sound', e.target.checked)}
              className="w-4 h-4"
            />
          </label>
          <label className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Vibrate className="w-4 h-4" />
              Vibration
            </span>
            <input
              type="checkbox"
              checked={preferences.vibration}
              onChange={(e) => updatePreference('vibration', e.target.checked)}
              className="w-4 h-4"
            />
          </label>
          <label className="flex items-center justify-between">
            <span>Do Not Disturb</span>
            <input
              type="checkbox"
              checked={preferences.doNotDisturb}
              onChange={(e) => updatePreference('doNotDisturb', e.target.checked)}
              className="w-4 h-4"
            />
          </label>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold mb-4">Notification Types</h3>
        <div className="space-y-3">
          {Object.entries(preferences.types).map(([type, enabled]) => (
            <label key={type} className="flex items-center justify-between capitalize">
              <span>{type}</span>
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => updateTypePreference(type as NotificationType, e.target.checked)}
                className="w-4 h-4"
              />
            </label>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold mb-4">Priority Levels</h3>
        <div className="space-y-3">
          {Object.entries(preferences.priorities).map(([priority, enabled]) => (
            <label key={priority} className="flex items-center justify-between capitalize">
              <span>{priority}</span>
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => updatePriorityPreference(priority as NotificationPriority, e.target.checked)}
                className="w-4 h-4"
              />
            </label>
          ))}
        </div>
      </div>
    </div>
  );
};

export default NotificationSystem;
