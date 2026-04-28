import { Notification, NotificationType, NotificationPriority, NotificationAction } from '../components/NotificationSystem';

export interface NotificationTemplate {
  type: NotificationType;
  title: string;
  message: string;
  priority: NotificationPriority;
  duration?: number;
  persistent?: boolean;
  sound?: string;
  vibration?: boolean;
  actions?: NotificationAction[];
}

export interface ScheduledNotification {
  id: string;
  template: NotificationTemplate;
  scheduledTime: Date;
  recurring?: {
    type: 'daily' | 'weekly' | 'monthly';
    interval?: number;
  };
}

export interface NotificationRule {
  id: string;
  name: string;
  condition: (notification: Notification) => boolean;
  action: (notification: Notification) => void;
  enabled: boolean;
}

class NotificationManager {
  private static instance: NotificationManager;
  private scheduledNotifications: Map<string, ScheduledNotification> = new Map();
  private notificationRules: Map<string, NotificationRule> = new Map();
  private notificationHistory: Notification[] = [];
  private timers: Map<string, ReturnType<typeof setTimeout>> = new Map();

  private constructor() {
    this.loadFromStorage();
    this.startScheduler();
  }

  public static getInstance(): NotificationManager {
    if (!NotificationManager.instance) {
      NotificationManager.instance = new NotificationManager();
    }
    return NotificationManager.instance;
  }

  private loadFromStorage(): void {
    try {
      const scheduled = localStorage.getItem('scheduled-notifications');
      if (scheduled) {
        const parsed = JSON.parse(scheduled);
        parsed.forEach((item: ScheduledNotification) => {
          item.scheduledTime = new Date(item.scheduledTime);
          this.scheduledNotifications.set(item.id, item);
        });
      }

      const rules = localStorage.getItem('notification-rules');
      if (rules) {
        const parsed = JSON.parse(rules);
        parsed.forEach((rule: NotificationRule) => {
          this.notificationRules.set(rule.id, rule);
        });
      }

      const history = localStorage.getItem('notification-history');
      if (history) {
        const parsed = JSON.parse(history);
        this.notificationHistory = parsed.map((n: any) => ({
          ...n,
          timestamp: new Date(n.timestamp)
        }));
      }
    } catch (error) {
      console.error('Failed to load notification manager data:', error);
    }
  }

  private saveToStorage(): void {
    try {
      const scheduled = Array.from(this.scheduledNotifications.values()).map(item => ({
        ...item,
        scheduledTime: item.scheduledTime.toISOString()
      }));
      localStorage.setItem('scheduled-notifications', JSON.stringify(scheduled));

      const rules = Array.from(this.notificationRules.values());
      localStorage.setItem('notification-rules', JSON.stringify(rules));

      const history = this.notificationHistory.slice(-100).map(n => ({
        ...n,
        timestamp: n.timestamp.toISOString()
      }));
      localStorage.setItem('notification-history', JSON.stringify(history));
    } catch (error) {
      console.error('Failed to save notification manager data:', error);
    }
  }

  private startScheduler(): void {
    setInterval(() => {
      this.checkScheduledNotifications();
    }, 60000); // Check every minute
  }

  private checkScheduledNotifications(): void {
    const now = new Date();

    for (const [id, scheduled] of this.scheduledNotifications) {
      if (scheduled.scheduledTime <= now) {
        this.triggerScheduledNotification(scheduled);

        if (scheduled.recurring) {
          this.scheduleNextRecurring(id, scheduled);
        } else {
          this.scheduledNotifications.delete(id);
          this.timers.delete(id);
        }
      }
    }

    this.saveToStorage();
  }

  private scheduleNextRecurring(id: string, scheduled: ScheduledNotification): void {
    const nextTime = new Date(scheduled.scheduledTime);

    switch (scheduled.recurring!.type) {
      case 'daily':
        nextTime.setDate(nextTime.getDate() + (scheduled.recurring!.interval || 1));
        break;
      case 'weekly':
        nextTime.setDate(nextTime.getDate() + (7 * (scheduled.recurring!.interval || 1)));
        break;
      case 'monthly':
        nextTime.setMonth(nextTime.getMonth() + (scheduled.recurring!.interval || 1));
        break;
    }

    scheduled.scheduledTime = nextTime;
    this.scheduledNotifications.set(id, scheduled);
  }

  private triggerScheduledNotification(scheduled: ScheduledNotification): void {
    const notification: Notification = {
      ...scheduled.template,
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date(),
      read: false
    };

    this.addToHistory(notification);
    this.applyRules(notification);

    if ((window as any).addNotification) {
      (window as any).addNotification(notification);
    }
  }

  private addToHistory(notification: Notification): void {
    this.notificationHistory.unshift(notification);
    if (this.notificationHistory.length > 1000) {
      this.notificationHistory = this.notificationHistory.slice(0, 1000);
    }
  }

  private applyRules(notification: Notification): void {
    for (const rule of this.notificationRules.values()) {
      if (rule.enabled && rule.condition(notification)) {
        try {
          rule.action(notification);
        } catch (error) {
          console.error('Error applying notification rule:', error);
        }
      }
    }
  }

  public scheduleNotification(template: NotificationTemplate, scheduledTime: Date, recurring?: ScheduledNotification['recurring']): string {
    const id = Math.random().toString(36).substr(2, 9);
    const scheduled: ScheduledNotification = {
      id,
      template,
      scheduledTime,
      recurring
    };

    this.scheduledNotifications.set(id, scheduled);
    this.saveToStorage();

    return id;
  }

  public cancelScheduledNotification(id: string): boolean {
    const cancelled = this.scheduledNotifications.delete(id);
    if (cancelled) {
      this.timers.delete(id);
      this.saveToStorage();
    }
    return cancelled;
  }

  public getScheduledNotifications(): ScheduledNotification[] {
    return Array.from(this.scheduledNotifications.values()).sort((a, b) =>
      a.scheduledTime.getTime() - b.scheduledTime.getTime()
    );
  }

  public addRule(rule: Omit<NotificationRule, 'id'>): string {
    const id = Math.random().toString(36).substr(2, 9);
    const fullRule: NotificationRule = { ...rule, id };
    this.notificationRules.set(id, fullRule);
    this.saveToStorage();
    return id;
  }

  public removeRule(id: string): boolean {
    const removed = this.notificationRules.delete(id);
    if (removed) {
      this.saveToStorage();
    }
    return removed;
  }

  public updateRule(id: string, updates: Partial<NotificationRule>): boolean {
    const rule = this.notificationRules.get(id);
    if (rule) {
      const updatedRule = { ...rule, ...updates };
      this.notificationRules.set(id, updatedRule);
      this.saveToStorage();
      return true;
    }
    return false;
  }

  public getRules(): NotificationRule[] {
    return Array.from(this.notificationRules.values());
  }

  public getHistory(filter?: {
    type?: NotificationType;
    priority?: NotificationPriority;
    startDate?: Date;
    endDate?: Date;
    search?: string;
  }): Notification[] {
    let filtered = [...this.notificationHistory];

    if (filter) {
      if (filter.type) {
        filtered = filtered.filter(n => n.type === filter.type);
      }

      if (filter.priority) {
        filtered = filtered.filter(n => n.priority === filter.priority);
      }

      if (filter.startDate) {
        filtered = filtered.filter(n => n.timestamp >= filter.startDate!);
      }

      if (filter.endDate) {
        filtered = filtered.filter(n => n.timestamp <= filter.endDate!);
      }

      if (filter.search) {
        const search = filter.search.toLowerCase();
        filtered = filtered.filter(n =>
          n.title.toLowerCase().includes(search) ||
          n.message.toLowerCase().includes(search)
        );
      }
    }

    return filtered;
  }

  public clearHistory(): void {
    this.notificationHistory = [];
    this.saveToStorage();
  }

  public getStats(): {
    total: number;
    byType: Record<NotificationType, number>;
    byPriority: Record<NotificationPriority, number>;
    recent: Notification[];
  } {
    const stats = {
      total: this.notificationHistory.length,
      byType: {} as Record<NotificationType, number>,
      byPriority: {} as Record<NotificationPriority, number>,
      recent: this.notificationHistory.slice(0, 10)
    };

    this.notificationHistory.forEach(notification => {
      stats.byType[notification.type] = (stats.byType[notification.type] || 0) + 1;
      stats.byPriority[notification.priority] = (stats.byPriority[notification.priority] || 0) + 1;
    });

    return stats;
  }

  public createNotification(type: NotificationType, customData?: Partial<NotificationTemplate>): NotificationTemplate {
    const templates: Record<NotificationType, NotificationTemplate> = {
      success: {
        type: 'success',
        title: 'Success',
        message: 'Operation completed successfully',
        priority: 'medium',
        duration: 4000,
        sound: 'success'
      },
      error: {
        type: 'error',
        title: 'Error',
        message: 'An error occurred',
        priority: 'high',
        duration: 8000,
        persistent: true,
        sound: 'error'
      },
      warning: {
        type: 'warning',
        title: 'Warning',
        message: 'Please review this warning',
        priority: 'medium',
        duration: 6000
      },
      info: {
        type: 'info',
        title: 'Information',
        message: 'Here\'s some information for you',
        priority: 'low',
        duration: 4000
      },
      classification: {
        type: 'classification',
        title: 'Food Classification Complete',
        message: 'Your food has been classified',
        priority: 'medium',
        duration: 5000,
        sound: 'classification'
      }
    };

    const template = templates[type];
    return { ...template, ...customData };
  }

  public notifyClassificationResult(result: {
    foodName: string;
    confidence: number;
    imageUrl: string;
  }): void {
    const notification = this.createNotification('classification', {
      title: `${result.foodName} Identified`,
      message: `Confidence: ${(result.confidence * 100).toFixed(1)}%`,
      priority: result.confidence > 0.8 ? 'high' : result.confidence > 0.6 ? 'medium' : 'low',
      actions: [
        {
          id: 'view',
          label: 'View Details',
          action: () => {
            window.location.href = `/classification/${result.foodName}`;
          },
          primary: true
        },
        {
          id: 'share',
          label: 'Share',
          action: () => {
            if (navigator.share) {
              navigator.share({
                title: 'Food Classification Result',
                text: `I just classified ${result.foodName} with ${(result.confidence * 100).toFixed(1)}% confidence!`,
                url: window.location.href
              });
            }
          }
        }
      ]
    });

    if ((window as any).addNotification) {
      (window as any).addNotification(notification);
    }
  }

  public notifyOfflineStatus(online: boolean): void {
    const notification = this.createNotification(online ? 'success' : 'warning', {
      title: online ? 'Connection Restored' : 'Offline Mode',
      message: online
        ? 'You are back online'
        : 'You are currently offline. Some features may be limited.',
      priority: online ? 'low' : 'medium',
      persistent: !online
    });

    if ((window as any).addNotification) {
      (window as any).addNotification(notification);
    }
  }

  public notifyStorageWarning(usage: number, limit: number): void {
    const percentage = (usage / limit) * 100;
    const notification = this.createNotification(
      percentage > 90 ? 'error' : 'warning',
      {
        title: 'Storage Space Warning',
        message: `You have used ${percentage.toFixed(1)}% of your storage space`,
        priority: percentage > 90 ? 'high' : 'medium',
        persistent: percentage > 90,
        actions: [
          {
            id: 'manage',
            label: 'Manage Storage',
            action: () => {
              window.location.href = '/settings/storage';
            },
            primary: true
          }
        ]
      }
    );

    if ((window as any).addNotification) {
      (window as any).addNotification(notification);
    }
  }

  public destroy(): void {
    this.timers.forEach(timer => clearTimeout(timer));
    this.timers.clear();
    this.saveToStorage();
  }
}

export const notificationManager = NotificationManager.getInstance();

export default notificationManager;
