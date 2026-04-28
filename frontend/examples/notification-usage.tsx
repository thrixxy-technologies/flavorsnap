import React, { useEffect } from 'react';
import { useNotifications } from '../hooks/useNotifications';
import { notificationManager } from '../utils/notificationManager';

const NotificationUsageExample: React.FC = () => {
  const { addNotification, preferences, updatePreferences } = useNotifications();

  useEffect(() => {
    // Example: Show classification result notification
    notificationManager.notifyClassificationResult({
      foodName: 'Apple',
      confidence: 0.95,
      imageUrl: '/images/apple.jpg'
    });

    // Example: Schedule a daily reminder
    const reminderId = notificationManager.scheduleNotification(
      notificationManager.createNotification('info', {
        title: 'Daily Food Log',
        message: 'Don\'t forget to log your meals today!',
        priority: 'medium'
      }),
      new Date(Date.now() + 24 * 60 * 60 * 1000), // Tomorrow
      { type: 'daily' }
    );

    return () => {
      notificationManager.cancelScheduledNotification(reminderId);
    };
  }, []);

  const handleSuccessNotification = () => {
    addNotification({
      type: 'success',
      title: 'Success!',
      message: 'Your action was completed successfully.',
      priority: 'medium',
      duration: 4000,
      actions: [
        {
          id: 'undo',
          label: 'Undo',
          action: () => console.log('Undo action'),
          primary: false
        }
      ]
    });
  };

  const handleErrorNotification = () => {
    addNotification({
      type: 'error',
      title: 'Error Occurred',
      message: 'Something went wrong. Please try again.',
      priority: 'high',
      persistent: true,
      actions: [
        {
          id: 'retry',
          label: 'Retry',
          action: () => console.log('Retry action'),
          primary: true
        },
        {
          id: 'dismiss',
          label: 'Dismiss',
          action: () => console.log('Dismiss error'),
          primary: false
        }
      ]
    });
  };

  const handleClassificationNotification = () => {
    notificationManager.notifyClassificationResult({
      foodName: 'Pizza',
      confidence: 0.87,
      imageUrl: '/images/pizza.jpg'
    });
  };

  const toggleDoNotDisturb = () => {
    updatePreferences({
      doNotDisturb: !preferences.doNotDisturb
    });
  };

  const toggleSound = () => {
    updatePreferences({
      sound: !preferences.sound
    });
  };

  return (
    <div className="p-6 space-y-4">
      <h2 className="text-2xl font-bold mb-4">Notification System Examples</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <h3 className="font-semibold">Toast Notifications</h3>
          <button
            onClick={handleSuccessNotification}
            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
          >
            Show Success Notification
          </button>
          <button
            onClick={handleErrorNotification}
            className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
          >
            Show Error Notification
          </button>
          <button
            onClick={handleClassificationNotification}
            className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600"
          >
            Show Classification Result
          </button>
        </div>

        <div className="space-y-2">
          <h3 className="font-semibold">Notification Settings</h3>
          <button
            onClick={toggleDoNotDisturb}
            className={`px-4 py-2 rounded ${
              preferences.doNotDisturb 
                ? 'bg-gray-500 text-white' 
                : 'bg-gray-200 text-gray-700'
            }`}
          >
            Do Not Disturb: {preferences.doNotDisturb ? 'ON' : 'OFF'}
          </button>
          <button
            onClick={toggleSound}
            className={`px-4 py-2 rounded ${
              preferences.sound 
                ? 'bg-blue-500 text-white' 
                : 'bg-gray-200 text-gray-700'
            }`}
          >
            Sound: {preferences.sound ? 'ON' : 'OFF'}
          </button>
        </div>
      </div>

      <div className="mt-6 p-4 bg-gray-100 rounded">
        <h3 className="font-semibold mb-2">Features Implemented:</h3>
        <ul className="list-disc list-inside space-y-1 text-sm">
          <li>Toast notifications with actions and dismissal</li>
          <li>Push notifications for classification results</li>
          <li>In-app notification center with history</li>
          <li>Notification preferences and scheduling</li>
          <li>Sound and vibration options</li>
          <li>Notification history and search</li>
          <li>Do Not Disturb mode</li>
        </ul>
      </div>
    </div>
  );
};

export default NotificationUsageExample;
