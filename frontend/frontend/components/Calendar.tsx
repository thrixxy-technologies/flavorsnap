'use client';
// Comprehensive calendar component — month/week/day/agenda views,
// event CRUD, reminders, drag-and-drop, keyboard navigation, theming.

import React from 'react';
import '@/frontend/styles/calendar.css';
import { useCalendar } from '@/frontend/hooks/useCalendar';
import type { UseCalendarOptions } from '@/frontend/hooks/useCalendar';
import {
  CalendarEvent,
  CalendarTheme,
  ViewMode,
  Reminder,
  RecurrenceRule,
  DEFAULT_THEME,
  DARK_THEME,
  formatDate,
  isSameDay,
  isToday,
  getEventsForDay,
  getDayHours,
  expandRecurringEvents,
  startOfMonth,
  endOfMonth,
} from '@/frontend/utils/calendarUtils';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface CalendarProps extends UseCalendarOptions {
  /** Additional CSS class on the root element */
  className?: string;
  /** Controlled theme override */
  theme?: CalendarTheme;
  /** Called when the user requests a browser notification for a reminder */
  onReminderFire?: (reminder: Reminder, event: CalendarEvent) => void;
}

// ─── Event form modal ─────────────────────────────────────────────────────────

interface EventFormProps {
  event?: CalendarEvent | null;
  defaultDate?: Date;
  onSave: (data: Omit<CalendarEvent, 'id'>) => void;
  onDelete?: () => void;
  onClose: () => void;
  onAddReminder: (minutesBefore: number, method: Reminder['method']) => void;
  onRemoveReminder: (reminderId: string) => void;
}

function EventForm({
  event,
  defaultDate,
  onSave,
  onDelete,
  onClose,
  onAddReminder,
  onRemoveReminder,
}: EventFormProps): React.ReactElement {
  const toDatetimeLocal = (d: Date) => {
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  const base = defaultDate ?? new Date();
  const defaultStart = event ? toDatetimeLocal(event.start) : toDatetimeLocal(base);
  const defaultEnd = event
    ? toDatetimeLocal(event.end)
    : toDatetimeLocal(new Date(base.getTime() + 60 * 60_000));

  const [title, setTitle] = React.useState(event?.title ?? '');
  const [description, setDescription] = React.useState(event?.description ?? '');
  const [start, setStart] = React.useState(defaultStart);
  const [end, setEnd] = React.useState(defaultEnd);
  const [color, setColor] = React.useState(event?.color ?? '#3b82f6');
  const [allDay, setAllDay] = React.useState(event?.allDay ?? false);
  const [recurrence, setRecurrence] = React.useState<RecurrenceRule>(event?.recurrence ?? 'none');
  const [reminderMinutes, setReminderMinutes] = React.useState(15);
  const [reminderMethod, setReminderMethod] = React.useState<Reminder['method']>('notification');

  const titleRef = React.useRef<HTMLInputElement>(null);

  // Focus title on mount
  React.useEffect(() => { titleRef.current?.focus(); }, []);

  // Close on Escape
  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    onSave({
      title: title.trim(),
      description: description.trim() || undefined,
      start: new Date(start),
      end: new Date(end),
      color,
      allDay,
      recurrence,
      reminders: event?.reminders ?? [],
      draggable: true,
    });
  };

  return (
    <div
      className="cal-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cal-modal-title"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="cal-modal">
        <h2 id="cal-modal-title" className="cal-modal-title">
          {event ? 'Edit Event' : 'New Event'}
        </h2>

        <form onSubmit={handleSubmit} noValidate>
          <div className="cal-form-group">
            <label className="cal-form-label" htmlFor="cal-title">Title *</label>
            <input
              id="cal-title"
              ref={titleRef}
              className="cal-form-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              aria-required="true"
            />
          </div>

          <div className="cal-form-group" style={{ marginTop: '0.75rem' }}>
            <label className="cal-form-label" htmlFor="cal-desc">Description</label>
            <textarea
              id="cal-desc"
              className="cal-form-textarea"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
            <div className="cal-form-group" style={{ flex: 1 }}>
              <label className="cal-form-label" htmlFor="cal-start">Start</label>
              <input
                id="cal-start"
                type="datetime-local"
                className="cal-form-input"
                value={start}
                onChange={(e) => setStart(e.target.value)}
              />
            </div>
            <div className="cal-form-group" style={{ flex: 1 }}>
              <label className="cal-form-label" htmlFor="cal-end">End</label>
              <input
                id="cal-end"
                type="datetime-local"
                className="cal-form-input"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <div className="cal-form-group">
              <label className="cal-form-label" htmlFor="cal-color">Color</label>
              <input
                id="cal-color"
                type="color"
                className="cal-form-input"
                style={{ width: '3rem', height: '2.25rem', padding: '0.125rem' }}
                value={color}
                onChange={(e) => setColor(e.target.value)}
              />
            </div>

            <div className="cal-form-group">
              <label className="cal-form-label" htmlFor="cal-recurrence">Repeat</label>
              <select
                id="cal-recurrence"
                className="cal-form-select"
                value={recurrence}
                onChange={(e) => setRecurrence(e.target.value as RecurrenceRule)}
              >
                <option value="none">None</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="yearly">Yearly</option>
              </select>
            </div>

            <div className="cal-form-group" style={{ flexDirection: 'row', alignItems: 'center', gap: '0.5rem', marginTop: '1.25rem' }}>
              <input
                id="cal-allday"
                type="checkbox"
                checked={allDay}
                onChange={(e) => setAllDay(e.target.checked)}
              />
              <label htmlFor="cal-allday" className="cal-form-label" style={{ marginBottom: 0 }}>All day</label>
            </div>
          </div>

          {/* Reminders */}
          {event && (
            <div style={{ marginTop: '0.75rem' }}>
              <p className="cal-form-label" style={{ marginBottom: '0.375rem' }}>Reminders</p>
              <div className="cal-reminders">
                {(event.reminders ?? []).map((r) => (
                  <div key={r.id} className="cal-reminder-item">
                    <span>{r.minutesBefore} min before ({r.method})</span>
                    <button
                      type="button"
                      className="cal-reminder-remove"
                      aria-label={`Remove reminder ${r.minutesBefore} minutes before`}
                      onClick={() => onRemoveReminder(r.id)}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
                <input
                  type="number"
                  className="cal-form-input"
                  style={{ width: '5rem' }}
                  value={reminderMinutes}
                  min={1}
                  onChange={(e) => setReminderMinutes(Number(e.target.value))}
                  aria-label="Minutes before reminder"
                />
                <select
                  className="cal-form-select"
                  value={reminderMethod}
                  onChange={(e) => setReminderMethod(e.target.value as Reminder['method'])}
                  aria-label="Reminder method"
                >
                  <option value="notification">Notification</option>
                  <option value="email">Email</option>
                </select>
                <button
                  type="button"
                  className="cal-btn"
                  onClick={() => onAddReminder(reminderMinutes, reminderMethod)}
                >
                  + Add
                </button>
              </div>
            </div>
          )}

          <div className="cal-modal-actions">
            {onDelete && (
              <button type="button" className="cal-btn cal-btn--danger" onClick={onDelete}>
                Delete
              </button>
            )}
            <button type="button" className="cal-btn" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="cal-btn cal-btn--primary">
              {event ? 'Save' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Month view ───────────────────────────────────────────────────────────────

const WEEKDAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

interface MonthViewProps {
  visibleDates: Date[];
  currentDate: Date;
  events: CalendarEvent[];
  onDayClick: (date: Date) => void;
  onEventClick: (event: CalendarEvent, e: React.MouseEvent) => void;
  onEventDragStart: (eventId: string) => void;
  onDayDrop: (date: Date) => void;
  draggingId: string | null;
}

function MonthView({
  visibleDates,
  currentDate,
  events,
  onDayClick,
  onEventClick,
  onEventDragStart,
  onDayDrop,
  draggingId,
}: MonthViewProps): React.ReactElement {
  const [dragOverDate, setDragOverDate] = React.useState<Date | null>(null);

  // Expand recurring events for the visible range
  const rangeStart = visibleDates[0];
  const rangeEnd = visibleDates[visibleDates.length - 1];
  const expanded = React.useMemo(
    () => expandRecurringEvents(events, rangeStart, rangeEnd),
    [events, rangeStart, rangeEnd],
  );

  return (
    <div className="cal-month" role="grid" aria-label="Month view">
      {/* Weekday headers */}
      <div className="cal-weekday-header" role="row">
        {WEEKDAY_LABELS.map((d) => (
          <div key={d} className="cal-weekday-cell" role="columnheader" aria-label={d}>
            {d}
          </div>
        ))}
      </div>

      {/* Day grid */}
      <div className="cal-month-grid">
        {visibleDates.map((day) => {
          const dayEvents = getEventsForDay(expanded, day);
          const isCurrentMonth = day.getMonth() === currentDate.getMonth();
          const today = isToday(day);
          const isDragOver = dragOverDate ? isSameDay(dragOverDate, day) : false;

          return (
            <div
              key={day.toISOString()}
              role="gridcell"
              aria-label={formatDate(day, 'long')}
              aria-current={today ? 'date' : undefined}
              className={[
                'cal-day-cell',
                today ? 'cal-day-cell--today' : '',
                !isCurrentMonth ? 'cal-day-cell--other-month' : '',
                isDragOver ? 'cal-day-cell--selected' : '',
              ].join(' ')}
              onClick={() => onDayClick(day)}
              onDragOver={(e) => { e.preventDefault(); setDragOverDate(day); }}
              onDragLeave={() => setDragOverDate(null)}
              onDrop={() => { onDayDrop(day); setDragOverDate(null); }}
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onDayClick(day); }}
            >
              <span className={`cal-day-number${today ? ' cal-day-number--today' : ''}`}>
                {day.getDate()}
              </span>
              {dayEvents.slice(0, 3).map((ev) => (
                <EventChip
                  key={ev.id}
                  event={ev}
                  onClick={onEventClick}
                  onDragStart={onEventDragStart}
                  isDragging={draggingId === ev.id}
                />
              ))}
              {dayEvents.length > 3 && (
                <span style={{ fontSize: '0.6875rem', opacity: 0.6, paddingLeft: '0.25rem' }}>
                  +{dayEvents.length - 3} more
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Week view ────────────────────────────────────────────────────────────────

interface WeekViewProps {
  weekDays: Date[];
  events: CalendarEvent[];
  onSlotClick: (date: Date, hour: number) => void;
  onEventClick: (event: CalendarEvent, e: React.MouseEvent) => void;
  onEventDragStart: (eventId: string) => void;
  onSlotDrop: (date: Date, hour: number) => void;
  draggingId: string | null;
}

function WeekView({
  weekDays,
  events,
  onSlotClick,
  onEventClick,
  onEventDragStart,
  onSlotDrop,
  draggingId,
}: WeekViewProps): React.ReactElement {
  const hours = getDayHours();
  const rangeStart = weekDays[0];
  const rangeEnd = weekDays[weekDays.length - 1];
  const expanded = React.useMemo(
    () => expandRecurringEvents(events, rangeStart, rangeEnd),
    [events, rangeStart, rangeEnd],
  );

  return (
    <div className="cal-week" role="grid" aria-label="Week view">
      {/* Header row */}
      <div className="cal-week-header" role="row">
        <div className="cal-time-slot" aria-hidden="true" />
        {weekDays.map((day) => (
          <div
            key={day.toISOString()}
            role="columnheader"
            aria-label={formatDate(day, 'long')}
            aria-current={isToday(day) ? 'date' : undefined}
            className={`cal-week-header-cell${isToday(day) ? ' cal-week-header-cell--today' : ''}`}
          >
            <div>{WEEKDAY_LABELS[day.getDay()]}</div>
            <span className={`cal-day-number${isToday(day) ? ' cal-day-number--today' : ''}`}>
              {day.getDate()}
            </span>
          </div>
        ))}
      </div>

      {/* Time grid */}
      <div className="cal-week-body">
        {/* Time gutter */}
        <div className="cal-time-gutter" aria-hidden="true">
          {hours.map((h) => (
            <div key={h} className="cal-time-slot">
              {h === 0 ? '' : `${h}:00`}
            </div>
          ))}
        </div>

        {/* Day columns */}
        {weekDays.map((day) => {
          const dayEvents = getEventsForDay(expanded, day);
          return (
            <div key={day.toISOString()} className="cal-week-col" role="gridcell">
              {hours.map((h) => (
                <div
                  key={h}
                  className="cal-week-hour-cell"
                  aria-label={`${formatDate(day, 'short')} ${h}:00`}
                  onClick={() => onSlotClick(day, h)}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => onSlotDrop(day, h)}
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSlotClick(day, h); }}
                />
              ))}
              {/* Overlay events */}
              {dayEvents.map((ev) => (
                <EventChip
                  key={ev.id}
                  event={ev}
                  onClick={onEventClick}
                  onDragStart={onEventDragStart}
                  isDragging={draggingId === ev.id}
                />
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Day view ─────────────────────────────────────────────────────────────────

interface DayViewProps {
  currentDate: Date;
  events: CalendarEvent[];
  onSlotClick: (date: Date, hour: number) => void;
  onEventClick: (event: CalendarEvent, e: React.MouseEvent) => void;
  onEventDragStart: (eventId: string) => void;
  onSlotDrop: (date: Date, hour: number) => void;
  draggingId: string | null;
}

function DayView({
  currentDate,
  events,
  onSlotClick,
  onEventClick,
  onEventDragStart,
  onSlotDrop,
  draggingId,
}: DayViewProps): React.ReactElement {
  const hours = getDayHours();
  const dayEvents = React.useMemo(
    () => getEventsForDay(expandRecurringEvents(events, currentDate, currentDate), currentDate),
    [events, currentDate],
  );

  return (
    <div className="cal-day" role="grid" aria-label="Day view">
      <div className="cal-day-header" role="heading" aria-level={2}>
        {formatDate(currentDate, 'long')}
      </div>
      <div className="cal-day-body">
        <div className="cal-time-gutter" aria-hidden="true">
          {hours.map((h) => (
            <div key={h} className="cal-time-slot">{h === 0 ? '' : `${h}:00`}</div>
          ))}
        </div>
        <div style={{ position: 'relative' }}>
          {hours.map((h) => (
            <div
              key={h}
              className="cal-week-hour-cell"
              aria-label={`${h}:00`}
              onClick={() => onSlotClick(currentDate, h)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => onSlotDrop(currentDate, h)}
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSlotClick(currentDate, h); }}
            />
          ))}
          {dayEvents.map((ev) => (
            <EventChip
              key={ev.id}
              event={ev}
              onClick={onEventClick}
              onDragStart={onEventDragStart}
              isDragging={draggingId === ev.id}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Agenda view ──────────────────────────────────────────────────────────────

interface AgendaViewProps {
  currentDate: Date;
  events: CalendarEvent[];
  onEventClick: (event: CalendarEvent, e: React.MouseEvent) => void;
}

function AgendaView({ currentDate, events, onEventClick }: AgendaViewProps): React.ReactElement {
  // Show 30 days from current date
  const rangeStart = new Date(currentDate);
  const rangeEnd = new Date(currentDate);
  rangeEnd.setDate(rangeEnd.getDate() + 30);

  const expanded = React.useMemo(
    () => expandRecurringEvents(events, rangeStart, rangeEnd),
    [events, rangeStart, rangeEnd],
  );

  // Group by day
  const grouped = React.useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (let d = new Date(rangeStart); d <= rangeEnd; d.setDate(d.getDate() + 1)) {
      const key = d.toDateString();
      const dayEvents = getEventsForDay(expanded, new Date(d));
      if (dayEvents.length > 0) map.set(key, dayEvents);
    }
    return map;
  }, [expanded, rangeStart, rangeEnd]);

  if (grouped.size === 0) {
    return (
      <div className="cal-agenda" role="list" aria-label="Agenda view">
        <p style={{ padding: '1rem', opacity: 0.5, textAlign: 'center' }}>No events in the next 30 days.</p>
      </div>
    );
  }

  return (
    <div className="cal-agenda" role="list" aria-label="Agenda view">
      {Array.from(grouped.entries()).map(([dateStr, dayEvents]) => (
        <div key={dateStr} className="cal-agenda-group" role="listitem">
          <div className="cal-agenda-date">{formatDate(new Date(dateStr), 'long')}</div>
          {dayEvents.map((ev) => (
            <div
              key={ev.id}
              className="cal-agenda-event"
              role="button"
              tabIndex={0}
              aria-label={`${ev.title}, ${formatDate(ev.start, 'time')} to ${formatDate(ev.end, 'time')}`}
              onClick={(e) => onEventClick(ev, e)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onEventClick(ev, e as unknown as React.MouseEvent); }}
            >
              <div
                className="cal-agenda-event-color"
                style={{ background: ev.color ?? DEFAULT_THEME.eventDefault }}
                aria-hidden="true"
              />
              <span className="cal-agenda-event-time">
                {ev.allDay ? 'All day' : `${formatDate(ev.start, 'time')} – ${formatDate(ev.end, 'time')}`}
              </span>
              <span className="cal-agenda-event-title">{ev.title}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

// ─── Event chip (shared) ──────────────────────────────────────────────────────

interface EventChipProps {
  event: CalendarEvent;
  onClick: (event: CalendarEvent, e: React.MouseEvent) => void;
  onDragStart: (eventId: string) => void;
  isDragging: boolean;
}

function EventChip({ event, onClick, onDragStart, isDragging }: EventChipProps): React.ReactElement {
  return (
    <div
      className={`cal-event${isDragging ? ' cal-event--dragging' : ''}`}
      style={{ background: event.color ?? DEFAULT_THEME.eventDefault }}
      role="button"
      tabIndex={0}
      aria-label={event.title}
      draggable={event.draggable !== false}
      onDragStart={(e) => { e.stopPropagation(); onDragStart(event.id); }}
      onClick={(e) => { e.stopPropagation(); onClick(event, e); }}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.stopPropagation();
          onClick(event, e as unknown as React.MouseEvent);
        }
      }}
    >
      <span className="cal-sr-only">Event: </span>
      {event.title}
    </div>
  );
}

// ─── Toolbar ──────────────────────────────────────────────────────────────────

interface ToolbarProps {
  currentDate: Date;
  view: ViewMode;
  onPrev: () => void;
  onNext: () => void;
  onToday: () => void;
  onViewChange: (v: ViewMode) => void;
  onNewEvent: () => void;
  onToggleTheme: () => void;
  isDark: boolean;
}

function Toolbar({
  currentDate,
  view,
  onPrev,
  onNext,
  onToday,
  onViewChange,
  onNewEvent,
  onToggleTheme,
  isDark,
}: ToolbarProps): React.ReactElement {
  const title = React.useMemo(() => {
    if (view === 'month') {
      return currentDate.toLocaleDateString([], { month: 'long', year: 'numeric' });
    }
    if (view === 'week') {
      return `Week of ${formatDate(currentDate, 'short')}`;
    }
    if (view === 'day') {
      return formatDate(currentDate, 'long');
    }
    return `Agenda — ${formatDate(currentDate, 'short')}`;
  }, [currentDate, view]);

  const views: ViewMode[] = ['month', 'week', 'day', 'agenda'];

  return (
    <div className="cal-toolbar" role="toolbar" aria-label="Calendar controls">
      {/* Navigation */}
      <div className="cal-toolbar-nav">
        <button
          className="cal-btn cal-btn--today"
          onClick={onToday}
          aria-label="Go to today"
        >
          Today
        </button>
        <button className="cal-btn" onClick={onPrev} aria-label="Previous period">‹</button>
        <button className="cal-btn" onClick={onNext} aria-label="Next period">›</button>
      </div>

      {/* Title */}
      <h2 className="cal-toolbar-title" aria-live="polite" aria-atomic="true">
        {title}
      </h2>

      {/* View switcher */}
      <div className="cal-view-switcher" role="group" aria-label="View mode">
        {views.map((v) => (
          <button
            key={v}
            className={`cal-btn${view === v ? ' cal-btn--active' : ''}`}
            onClick={() => onViewChange(v)}
            aria-pressed={view === v}
            aria-label={`${v} view`}
          >
            {v.charAt(0).toUpperCase() + v.slice(1)}
          </button>
        ))}
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: '0.25rem' }}>
        <button className="cal-btn cal-btn--primary" onClick={onNewEvent} aria-label="Create new event">
          + Event
        </button>
        <button
          className="cal-btn"
          onClick={onToggleTheme}
          aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
          title={isDark ? 'Light mode' : 'Dark mode'}
        >
          {isDark ? '☀️' : '🌙'}
        </button>
      </div>
    </div>
  );
}

// ─── Main Calendar component ──────────────────────────────────────────────────

export default function Calendar({
  className = '',
  theme: themeProp,
  onReminderFire,
  ...calendarOptions
}: CalendarProps): React.ReactElement {
  const cal = useCalendar({ ...calendarOptions, onReminderFire });

  // Theme toggle (light ↔ dark)
  const [isDark, setIsDark] = React.useState(false);
  const activeTheme = themeProp ?? (isDark ? DARK_THEME : DEFAULT_THEME);

  // Modal state
  const [modalOpen, setModalOpen] = React.useState(false);
  const [modalDefaultDate, setModalDefaultDate] = React.useState<Date | undefined>();

  // Drag state
  const [draggingId, setDraggingId] = React.useState<string | null>(null);

  // Apply CSS custom properties from theme
  const cssVars = {
    '--cal-primary':    activeTheme.primary,
    '--cal-secondary':  activeTheme.secondary,
    '--cal-bg':         activeTheme.background,
    '--cal-surface':    activeTheme.surface,
    '--cal-text':       activeTheme.text,
    '--cal-border':     activeTheme.border,
    '--cal-event-bg':   activeTheme.eventDefault,
  } as React.CSSProperties;

  // Keyboard navigation on the root element
  const handleRootKeyDown = React.useCallback(
    (e: React.KeyboardEvent) => {
      if (modalOpen) return;
      if (e.key === 'ArrowLeft') { e.preventDefault(); cal.goToPrev(); }
      if (e.key === 'ArrowRight') { e.preventDefault(); cal.goToNext(); }
      if (e.key === 't' || e.key === 'T') cal.goToToday();
      if (e.key === 'n' || e.key === 'N') { setModalDefaultDate(undefined); setModalOpen(true); }
    },
    [cal, modalOpen],
  );

  const openNewEventModal = (date?: Date) => {
    setModalDefaultDate(date);
    cal.selectEvent(null);
    setModalOpen(true);
  };

  const openEditEventModal = (event: CalendarEvent, e: React.MouseEvent) => {
    e.stopPropagation();
    cal.selectEvent(event);
    setModalOpen(true);
  };

  const handleSave = (data: Omit<CalendarEvent, 'id'>) => {
    if (cal.selectedEvent) {
      cal.updateEvent(cal.selectedEvent.id, data);
    } else {
      cal.addEvent(data);
    }
    setModalOpen(false);
  };

  const handleDelete = () => {
    if (cal.selectedEvent) {
      cal.deleteEvent(cal.selectedEvent.id);
      setModalOpen(false);
    }
  };

  const handleDayDrop = (date: Date) => {
    if (!draggingId) return;
    const newStart = new Date(date);
    newStart.setHours(9, 0, 0, 0);
    cal.dragEvent(draggingId, newStart);
    setDraggingId(null);
  };

  const handleSlotDrop = (date: Date, hour: number) => {
    if (!draggingId) return;
    const newStart = new Date(date);
    newStart.setHours(hour, 0, 0, 0);
    cal.dragEvent(draggingId, newStart);
    setDraggingId(null);
  };

  return (
    <div
      className={`cal-root ${className}`}
      style={cssVars}
      role="application"
      aria-label="Calendar"
      tabIndex={0}
      onKeyDown={handleRootKeyDown}
    >
      {/* Screen-reader instructions */}
      <p className="cal-sr-only">
        Use arrow keys to navigate between periods. Press N to create a new event. Press T to go to today.
      </p>

      <Toolbar
        currentDate={cal.currentDate}
        view={cal.view}
        onPrev={cal.goToPrev}
        onNext={cal.goToNext}
        onToday={cal.goToToday}
        onViewChange={cal.setView}
        onNewEvent={() => openNewEventModal()}
        onToggleTheme={() => setIsDark((d) => !d)}
        isDark={isDark}
      />

      {cal.view === 'month' && (
        <MonthView
          visibleDates={cal.visibleDates}
          currentDate={cal.currentDate}
          events={cal.events}
          onDayClick={(date) => openNewEventModal(date)}
          onEventClick={openEditEventModal}
          onEventDragStart={setDraggingId}
          onDayDrop={handleDayDrop}
          draggingId={draggingId}
        />
      )}

      {cal.view === 'week' && (
        <WeekView
          weekDays={cal.visibleDates}
          events={cal.events}
          onSlotClick={(date, hour) => {
            const d = new Date(date);
            d.setHours(hour, 0, 0, 0);
            openNewEventModal(d);
          }}
          onEventClick={openEditEventModal}
          onEventDragStart={setDraggingId}
          onSlotDrop={handleSlotDrop}
          draggingId={draggingId}
        />
      )}

      {cal.view === 'day' && (
        <DayView
          currentDate={cal.currentDate}
          events={cal.events}
          onSlotClick={(date, hour) => {
            const d = new Date(date);
            d.setHours(hour, 0, 0, 0);
            openNewEventModal(d);
          }}
          onEventClick={openEditEventModal}
          onEventDragStart={setDraggingId}
          onSlotDrop={handleSlotDrop}
          draggingId={draggingId}
        />
      )}

      {cal.view === 'agenda' && (
        <AgendaView
          currentDate={cal.currentDate}
          events={cal.events}
          onEventClick={openEditEventModal}
        />
      )}

      {modalOpen && (
        <EventForm
          event={cal.selectedEvent}
          defaultDate={modalDefaultDate}
          onSave={handleSave}
          onDelete={cal.selectedEvent ? handleDelete : undefined}
          onClose={() => setModalOpen(false)}
          onAddReminder={(mins, method) => {
            if (cal.selectedEvent) cal.addReminder(cal.selectedEvent.id, { minutesBefore: mins, method });
          }}
          onRemoveReminder={(reminderId) => {
            if (cal.selectedEvent) cal.removeReminder(cal.selectedEvent.id, reminderId);
          }}
        />
      )}
    </div>
  );
}
