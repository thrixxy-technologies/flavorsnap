// Calendar utility functions

export type ViewMode = 'month' | 'week' | 'day' | 'agenda';

export type RecurrenceRule = 'none' | 'daily' | 'weekly' | 'monthly' | 'yearly';

export interface CalendarEvent {
  id: string;
  title: string;
  description?: string;
  start: Date;
  end: Date;
  allDay?: boolean;
  color?: string;
  category?: string;
  recurrence?: RecurrenceRule;
  reminders?: Reminder[];
  draggable?: boolean;
}

export interface Reminder {
  id: string;
  eventId: string;
  minutesBefore: number;
  method: 'notification' | 'email';
  triggered?: boolean;
}

export interface CalendarTheme {
  primary: string;
  secondary: string;
  background: string;
  surface: string;
  text: string;
  border: string;
  eventDefault: string;
}

export const DEFAULT_THEME: CalendarTheme = {
  primary: '#3b82f6',
  secondary: '#6366f1',
  background: '#ffffff',
  surface: '#f9fafb',
  text: '#111827',
  border: '#e5e7eb',
  eventDefault: '#3b82f6',
};

export const DARK_THEME: CalendarTheme = {
  primary: '#60a5fa',
  secondary: '#818cf8',
  background: '#111827',
  surface: '#1f2937',
  text: '#f9fafb',
  border: '#374151',
  eventDefault: '#60a5fa',
};

/** Returns the start of the week (Sunday) for a given date */
export function startOfWeek(date: Date): Date {
  const d = new Date(date);
  d.setDate(d.getDate() - d.getDay());
  d.setHours(0, 0, 0, 0);
  return d;
}

/** Returns the start of the month for a given date */
export function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

/** Returns the end of the month for a given date */
export function endOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0, 23, 59, 59, 999);
}

/** Returns all days in the month grid (including padding days from prev/next months) */
export function getMonthGrid(date: Date): Date[] {
  const start = startOfMonth(date);
  const end = endOfMonth(date);
  const days: Date[] = [];

  // Pad start to Sunday
  const paddingStart = start.getDay();
  for (let i = paddingStart; i > 0; i--) {
    const d = new Date(start);
    d.setDate(d.getDate() - i);
    days.push(d);
  }

  // All days in month
  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    days.push(new Date(d));
  }

  // Pad end to Saturday (complete 6-week grid = 42 cells)
  while (days.length < 42) {
    const last = days[days.length - 1];
    const next = new Date(last);
    next.setDate(next.getDate() + 1);
    days.push(next);
  }

  return days;
}

/** Returns the 7 days of the week containing the given date */
export function getWeekDays(date: Date): Date[] {
  const start = startOfWeek(date);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    return d;
  });
}

/** Returns the hours of a single day (0–23) */
export function getDayHours(): number[] {
  return Array.from({ length: 24 }, (_, i) => i);
}

/** Checks if two dates are the same calendar day */
export function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

/** Checks if a date is today */
export function isToday(date: Date): boolean {
  return isSameDay(date, new Date());
}

/** Filters events that fall on a specific day */
export function getEventsForDay(events: CalendarEvent[], day: Date): CalendarEvent[] {
  return events.filter(
    (e) =>
      isSameDay(e.start, day) ||
      isSameDay(e.end, day) ||
      (e.start <= day && e.end >= day),
  );
}

/** Generates a unique ID */
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

/** Formats a date for display */
export function formatDate(date: Date, format: 'short' | 'long' | 'time' = 'short'): string {
  if (format === 'time') {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  if (format === 'long') {
    return date.toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  }
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

/** Expands recurring events within a date range */
export function expandRecurringEvents(
  events: CalendarEvent[],
  rangeStart: Date,
  rangeEnd: Date,
): CalendarEvent[] {
  const result: CalendarEvent[] = [];

  for (const event of events) {
    if (!event.recurrence || event.recurrence === 'none') {
      result.push(event);
      continue;
    }

    const duration = event.end.getTime() - event.start.getTime();
    let cursor = new Date(event.start);

    while (cursor <= rangeEnd) {
      if (cursor >= rangeStart) {
        result.push({
          ...event,
          id: `${event.id}-${cursor.getTime()}`,
          start: new Date(cursor),
          end: new Date(cursor.getTime() + duration),
        });
      }

      // Advance cursor by recurrence interval
      const next = new Date(cursor);
      switch (event.recurrence) {
        case 'daily':   next.setDate(next.getDate() + 1); break;
        case 'weekly':  next.setDate(next.getDate() + 7); break;
        case 'monthly': next.setMonth(next.getMonth() + 1); break;
        case 'yearly':  next.setFullYear(next.getFullYear() + 1); break;
      }
      if (next.getTime() === cursor.getTime()) break; // safety guard
      cursor = next;
    }
  }

  return result;
}

/** Checks which reminders should fire now and returns them */
export function getDueReminders(events: CalendarEvent[], now: Date = new Date()): Reminder[] {
  const due: Reminder[] = [];
  for (const event of events) {
    if (!event.reminders) continue;
    for (const reminder of event.reminders) {
      if (reminder.triggered) continue;
      const fireAt = new Date(event.start.getTime() - reminder.minutesBefore * 60_000);
      if (now >= fireAt) {
        due.push(reminder);
      }
    }
  }
  return due;
}

/** Moves an event to a new start date, preserving duration */
export function moveEvent(event: CalendarEvent, newStart: Date): CalendarEvent {
  const duration = event.end.getTime() - event.start.getTime();
  return { ...event, start: newStart, end: new Date(newStart.getTime() + duration) };
}
