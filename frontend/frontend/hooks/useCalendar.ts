// Hook for calendar state and event management

import React from 'react';
import {
  CalendarEvent,
  Reminder,
  ViewMode,
  CalendarTheme,
  DEFAULT_THEME,
  generateId,
  moveEvent,
  getDueReminders,
  getMonthGrid,
  getWeekDays,
  startOfMonth,
  startOfWeek,
} from '@/frontend/utils/calendarUtils';

export interface UseCalendarOptions {
  initialEvents?: CalendarEvent[];
  initialView?: ViewMode;
  theme?: CalendarTheme;
  onReminderFire?: (reminder: Reminder, event: CalendarEvent) => void;
}

export interface UseCalendarReturn {
  // State
  events: CalendarEvent[];
  currentDate: Date;
  view: ViewMode;
  theme: CalendarTheme;
  selectedEvent: CalendarEvent | null;
  // Navigation
  goToToday: () => void;
  goToPrev: () => void;
  goToNext: () => void;
  goToDate: (date: Date) => void;
  setView: (view: ViewMode) => void;
  // Event CRUD
  addEvent: (event: Omit<CalendarEvent, 'id'>) => CalendarEvent;
  updateEvent: (id: string, updates: Partial<CalendarEvent>) => void;
  deleteEvent: (id: string) => void;
  selectEvent: (event: CalendarEvent | null) => void;
  // Drag and drop
  dragEvent: (eventId: string, newStart: Date) => void;
  // Reminders
  addReminder: (eventId: string, reminder: Omit<Reminder, 'id' | 'eventId'>) => void;
  removeReminder: (eventId: string, reminderId: string) => void;
  // Theme
  setTheme: (theme: CalendarTheme) => void;
  // Derived
  visibleDates: Date[];
}

export function useCalendar({
  initialEvents = [],
  initialView = 'month',
  theme: initialTheme = DEFAULT_THEME,
  onReminderFire,
}: UseCalendarOptions = {}): UseCalendarReturn {
  const [events, setEvents] = React.useState<CalendarEvent[]>(initialEvents);
  const [currentDate, setCurrentDate] = React.useState<Date>(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  });
  const [view, setView] = React.useState<ViewMode>(initialView);
  const [theme, setTheme] = React.useState<CalendarTheme>(initialTheme);
  const [selectedEvent, setSelectedEvent] = React.useState<CalendarEvent | null>(null);

  // Reminder polling — checks every 30 seconds
  const onReminderFireRef = React.useRef(onReminderFire);
  onReminderFireRef.current = onReminderFire;

  React.useEffect(() => {
    const tick = () => {
      const due = getDueReminders(events);
      if (due.length === 0) return;

      setEvents((prev) =>
        prev.map((event) => {
          if (!event.reminders) return event;
          const updatedReminders = event.reminders.map((r) =>
            due.find((d) => d.id === r.id) ? { ...r, triggered: true } : r,
          );
          const fired = due.filter((d) => event.reminders!.some((r) => r.id === d.id));
          fired.forEach((r) => onReminderFireRef.current?.(r, event));
          return { ...event, reminders: updatedReminders };
        }),
      );
    };

    tick(); // run immediately on mount / event change
    const interval = setInterval(tick, 30_000);
    return () => clearInterval(interval);
  }, [events]);

  // Navigation helpers
  const goToToday = React.useCallback(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    setCurrentDate(d);
  }, []);

  const goToPrev = React.useCallback(() => {
    setCurrentDate((prev) => {
      const d = new Date(prev);
      if (view === 'month') d.setMonth(d.getMonth() - 1);
      else if (view === 'week') d.setDate(d.getDate() - 7);
      else d.setDate(d.getDate() - 1);
      return d;
    });
  }, [view]);

  const goToNext = React.useCallback(() => {
    setCurrentDate((prev) => {
      const d = new Date(prev);
      if (view === 'month') d.setMonth(d.getMonth() + 1);
      else if (view === 'week') d.setDate(d.getDate() + 7);
      else d.setDate(d.getDate() + 1);
      return d;
    });
  }, [view]);

  const goToDate = React.useCallback((date: Date) => {
    const d = new Date(date);
    d.setHours(0, 0, 0, 0);
    setCurrentDate(d);
  }, []);

  // Event CRUD
  const addEvent = React.useCallback((eventData: Omit<CalendarEvent, 'id'>): CalendarEvent => {
    const event: CalendarEvent = { ...eventData, id: generateId() };
    setEvents((prev) => [...prev, event]);
    return event;
  }, []);

  const updateEvent = React.useCallback((id: string, updates: Partial<CalendarEvent>) => {
    setEvents((prev) =>
      prev.map((e) => (e.id === id ? { ...e, ...updates } : e)),
    );
    setSelectedEvent((prev) => (prev?.id === id ? { ...prev, ...updates } : prev));
  }, []);

  const deleteEvent = React.useCallback((id: string) => {
    setEvents((prev) => prev.filter((e) => e.id !== id));
    setSelectedEvent((prev) => (prev?.id === id ? null : prev));
  }, []);

  const selectEvent = React.useCallback((event: CalendarEvent | null) => {
    setSelectedEvent(event);
  }, []);

  // Drag and drop
  const dragEvent = React.useCallback((eventId: string, newStart: Date) => {
    setEvents((prev) =>
      prev.map((e) => (e.id === eventId ? moveEvent(e, newStart) : e)),
    );
  }, []);

  // Reminders
  const addReminder = React.useCallback(
    (eventId: string, reminderData: Omit<Reminder, 'id' | 'eventId'>) => {
      const reminder: Reminder = { ...reminderData, id: generateId(), eventId };
      setEvents((prev) =>
        prev.map((e) =>
          e.id === eventId
            ? { ...e, reminders: [...(e.reminders ?? []), reminder] }
            : e,
        ),
      );
    },
    [],
  );

  const removeReminder = React.useCallback((eventId: string, reminderId: string) => {
    setEvents((prev) =>
      prev.map((e) =>
        e.id === eventId
          ? { ...e, reminders: (e.reminders ?? []).filter((r) => r.id !== reminderId) }
          : e,
      ),
    );
  }, []);

  // Derived: visible dates for current view
  const visibleDates = React.useMemo<Date[]>(() => {
    if (view === 'month') return getMonthGrid(currentDate);
    if (view === 'week') return getWeekDays(currentDate);
    return [new Date(currentDate)];
  }, [view, currentDate]);

  return {
    events,
    currentDate,
    view,
    theme,
    selectedEvent,
    goToToday,
    goToPrev,
    goToNext,
    goToDate,
    setView,
    addEvent,
    updateEvent,
    deleteEvent,
    selectEvent,
    dragEvent,
    addReminder,
    removeReminder,
    setTheme,
    visibleDates,
  };
}
