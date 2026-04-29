"""
Advanced Event Handling for Stream Processing
Implements complex event processing, pattern matching, and event correlation
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
import re
from collections import defaultdict, deque
import uuid
import hashlib

from stream_processor import StreamEvent

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Event types for processing"""
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"
    ANALYTICS_EVENT = "analytics_event"
    ERROR_EVENT = "error_event"
    BUSINESS_EVENT = "business_event"
    ML_INFERENCE = "ml_inference"
    CV_DETECTION = "cv_detection"
    NETWORK_EVENT = "network_event"

class EventPattern(Enum):
    """Event pattern types"""
    SEQUENCE = "sequence"
    FREQUENCY = "frequency"
    TEMPORAL = "temporal"
    CORRELATION = "correlation"
    ANOMALY = "anomaly"
    THRESHOLD = "threshold"

@dataclass
class EventPatternMatch:
    """Pattern match result"""
    pattern_id: str
    pattern_type: EventPattern
    matched_events: List[StreamEvent]
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class EventRule:
    """Event processing rule"""
    rule_id: str
    name: str
    description: str
    event_type: EventType
    pattern_type: EventPattern
    conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    enabled: bool = True
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)

class ComplexEventProcessor:
    """Complex event processor with pattern matching and correlation"""
    
    def __init__(self):
        self.rules: Dict[str, EventRule] = {}
        self.patterns: Dict[str, Dict[str, Any]] = {}
        self.event_sequences: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.event_counts: Dict[str, int] = defaultdict(int)
        self.event_windows: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.active_matches: Dict[str, EventPatternMatch] = {}
        
        # Pattern matching state
        self.sequence_states: Dict[str, List[StreamEvent]] = defaultdict(list)
        self.frequency_counters: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        self.logger = logging.getLogger('ComplexEventProcessor')
    
    def add_rule(self, rule: EventRule):
        """Add event processing rule"""
        self.rules[rule.rule_id] = rule
        self.logger.info(f"Added rule: {rule.name}")
    
    def remove_rule(self, rule_id: str):
        """Remove event processing rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            self.logger.info(f"Removed rule: {rule_id}")
    
    async def process_event(self, event: StreamEvent) -> List[EventPatternMatch]:
        """Process event and find pattern matches"""
        matches = []
        
        try:
            # Update event tracking
            await self._update_event_tracking(event)
            
            # Check all enabled rules
            for rule in self.rules.values():
                if not rule.enabled or rule.event_type.value != event.event_type:
                    continue
                
                match = await self._check_rule(rule, event)
                if match:
                    matches.append(match)
                    await self._execute_actions(rule, match)
            
            return matches
            
        except Exception as e:
            self.logger.error(f"Error processing event: {e}")
            return []
    
    async def _update_event_tracking(self, event: StreamEvent):
        """Update event tracking structures"""
        event_type = event.event_type
        
        # Update sequences
        self.event_sequences[event_type].append(event)
        
        # Update counts
        self.event_counts[event_type] += 1
        
        # Update time windows
        self.event_windows[event_type].append(event)
    
    async def _check_rule(self, rule: EventRule, event: StreamEvent) -> Optional[EventPatternMatch]:
        """Check if rule matches event"""
        try:
            if rule.pattern_type == EventPattern.SEQUENCE:
                return await self._check_sequence_pattern(rule, event)
            elif rule.pattern_type == EventPattern.FREQUENCY:
                return await self._check_frequency_pattern(rule, event)
            elif rule.pattern_type == EventPattern.TEMPORAL:
                return await self._check_temporal_pattern(rule, event)
            elif rule.pattern_type == EventPattern.CORRELATION:
                return await self._check_correlation_pattern(rule, event)
            elif rule.pattern_type == EventPattern.ANOMALY:
                return await self._check_anomaly_pattern(rule, event)
            elif rule.pattern_type == EventPattern.THRESHOLD:
                return await self._check_threshold_pattern(rule, event)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking rule {rule.rule_id}: {e}")
            return None
    
    async def _check_sequence_pattern(self, rule: EventRule, event: StreamEvent) -> Optional[EventPatternMatch]:
        """Check sequence pattern"""
        try:
            sequence_def = rule.conditions.get('sequence', [])
            max_time_gap = rule.conditions.get('max_time_gap_ms', 5000)
            
            # Get current sequence state
            state_key = f"{rule.rule_id}_sequence"
            current_sequence = self.sequence_states[state_key]
            
            # Add current event to sequence if it matches expected pattern
            if sequence_def and event.event_type == sequence_def[len(current_sequence) % len(sequence_def)]:
                current_sequence.append(event)
                
                # Check if sequence is complete
                if len(current_sequence) >= len(sequence_def):
                    # Check time constraints
                    if self._check_time_constraints(current_sequence, max_time_gap):
                        match = EventPatternMatch(
                            pattern_id=rule.rule_id,
                            pattern_type=EventPattern.SEQUENCE,
                            matched_events=current_sequence.copy(),
                            confidence=1.0,
                            metadata={'sequence_length': len(current_sequence)}
                        )
                        
                        # Reset sequence state
                        self.sequence_states[state_key] = []
                        return match
                else:
                    # Keep partial sequence
                    pass
            else:
                # Reset if event doesn't match expected sequence
                self.sequence_states[state_key] = []
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking sequence pattern: {e}")
            return None
    
    async def _check_frequency_pattern(self, rule: EventRule, event: StreamEvent) -> Optional[EventPatternMatch]:
        """Check frequency pattern"""
        try:
            threshold = rule.conditions.get('threshold', 10)
            time_window_ms = rule.conditions.get('time_window_ms', 60000)
            
            # Count events in time window
            current_time = event.timestamp
            window_start = current_time - timedelta(milliseconds=time_window_ms)
            
            recent_events = [
                e for e in self.event_sequences[event.event_type]
                if e.timestamp >= window_start
            ]
            
            if len(recent_events) >= threshold:
                match = EventPatternMatch(
                    pattern_id=rule.rule_id,
                    pattern_type=EventPattern.FREQUENCY,
                    matched_events=recent_events,
                    confidence=min(1.0, len(recent_events) / threshold),
                    metadata={
                        'count': len(recent_events),
                        'threshold': threshold,
                        'time_window_ms': time_window_ms
                    }
                )
                return match
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking frequency pattern: {e}")
            return None
    
    async def _check_temporal_pattern(self, rule: EventRule, event: StreamEvent) -> Optional[EventPatternMatch]:
        """Check temporal pattern"""
        try:
            time_constraints = rule.conditions.get('time_constraints', {})
            
            for constraint_name, constraint_value in time_constraints.items():
                if constraint_name == 'hour_of_day':
                    if event.timestamp.hour not in constraint_value:
                        return None
                elif constraint_name == 'day_of_week':
                    if event.timestamp.weekday() not in constraint_value:
                        return None
                elif constraint_name == 'time_between_events':
                    # Check time between consecutive events
                    if len(self.event_sequences[event.event_type]) > 1:
                        last_event = self.event_sequences[event.event_type][-2]
                        time_diff = (event.timestamp - last_event.timestamp).total_seconds() * 1000
                        min_gap, max_gap = constraint_value
                        if not (min_gap <= time_diff <= max_gap):
                            return None
            
            match = EventPatternMatch(
                pattern_id=rule.rule_id,
                pattern_type=EventPattern.TEMPORAL,
                matched_events=[event],
                confidence=1.0,
                metadata={'temporal_constraints': time_constraints}
            )
            return match
            
        except Exception as e:
            self.logger.error(f"Error checking temporal pattern: {e}")
            return None
    
    async def _check_correlation_pattern(self, rule: EventRule, event: StreamEvent) -> Optional[EventPatternMatch]:
        """Check correlation pattern between different event types"""
        try:
            correlation_rules = rule.conditions.get('correlations', [])
            time_window_ms = rule.conditions.get('time_window_ms', 30000)
            
            correlated_events = [event]
            current_time = event.timestamp
            window_start = current_time - timedelta(milliseconds=time_window_ms)
            
            for correlation in correlation_rules:
                target_event_type = correlation.get('event_type')
                field_match = correlation.get('field_match', {})
                
                # Find correlated events
                for target_event in self.event_sequences.get(target_event_type, []):
                    if target_event.timestamp < window_start:
                        continue
                    
                    # Check field correlations
                    matches_correlation = True
                    for field, condition in field_match.items():
                        if field in event.data and field in target_event.data:
                            event_value = event.data[field]
                            target_value = target_event.data[field]
                            
                            if condition.get('operator') == 'equals':
                                if event_value != target_value:
                                    matches_correlation = False
                                    break
                            elif condition.get('operator') == 'contains':
                                if str(target_value) not in str(event_value):
                                    matches_correlation = False
                                    break
                    
                    if matches_correlation:
                        correlated_events.append(target_event)
            
            # Check if minimum correlation threshold is met
            min_correlations = rule.conditions.get('min_correlations', 2)
            if len(correlated_events) >= min_correlations:
                match = EventPatternMatch(
                    pattern_id=rule.rule_id,
                    pattern_type=EventPattern.CORRELATION,
                    matched_events=correlated_events,
                    confidence=len(correlated_events) / min_correlations,
                    metadata={
                        'correlation_count': len(correlated_events),
                        'event_types': list(set(e.event_type for e in correlated_events))
                    }
                )
                return match
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking correlation pattern: {e}")
            return None
    
    async def _check_anomaly_pattern(self, rule: EventRule, event: StreamEvent) -> Optional[EventPatternMatch]:
        """Check anomaly pattern"""
        try:
            anomaly_type = rule.conditions.get('anomaly_type', 'statistical')
            threshold = rule.conditions.get('threshold', 2.0)
            field = rule.conditions.get('field', 'value')
            
            if anomaly_type == 'statistical':
                # Statistical anomaly detection
                values = []
                for e in self.event_sequences[event.event_type]:
                    if field in e.data and isinstance(e.data[field], (int, float)):
                        values.append(e.data[field])
                
                if len(values) < 10:  # Not enough data for statistical analysis
                    return None
                
                mean_val = np.mean(values)
                std_val = np.std(values)
                
                if field in event.data and isinstance(event.data[field], (int, float)):
                    z_score = abs(event.data[field] - mean_val) / std_val if std_val > 0 else 0
                    
                    if z_score > threshold:
                        match = EventPatternMatch(
                            pattern_id=rule.rule_id,
                            pattern_type=EventPattern.ANOMALY,
                            matched_events=[event],
                            confidence=min(1.0, z_score / threshold),
                            metadata={
                                'anomaly_type': anomaly_type,
                                'field': field,
                                'value': event.data[field],
                                'z_score': z_score,
                                'threshold': threshold
                            }
                        )
                        return match
            
            elif anomaly_type == 'frequency':
                # Frequency anomaly detection
                time_window_ms = rule.conditions.get('time_window_ms', 60000)
                current_time = event.timestamp
                window_start = current_time - timedelta(milliseconds=time_window_ms)
                
                recent_count = len([
                    e for e in self.event_sequences[event.event_type]
                    if e.timestamp >= window_start
                ])
                
                # Calculate historical average
                historical_window_ms = rule.conditions.get('historical_window_ms', 3600000)
                historical_start = current_time - timedelta(milliseconds=historical_window_ms)
                
                historical_count = len([
                    e for e in self.event_sequences[event.event_type]
                    if e.timestamp >= historical_start
                ])
                
                if historical_count > 0:
                    historical_rate = historical_count / (historical_window_ms / 1000)
                    current_rate = recent_count / (time_window_ms / 1000)
                    
                    if current_rate > historical_rate * threshold:
                        match = EventPatternMatch(
                            pattern_id=rule.rule_id,
                            pattern_type=EventPattern.ANOMALY,
                            matched_events=[event],
                            confidence=min(1.0, current_rate / (historical_rate * threshold)),
                            metadata={
                                'anomaly_type': anomaly_type,
                                'current_rate': current_rate,
                                'historical_rate': historical_rate,
                                'threshold': threshold
                            }
                        )
                        return match
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking anomaly pattern: {e}")
            return None
    
    async def _check_threshold_pattern(self, rule: EventRule, event: StreamEvent) -> Optional[EventPatternMatch]:
        """Check threshold pattern"""
        try:
            field = rule.conditions.get('field', 'value')
            operator = rule.conditions.get('operator', 'greater_than')
            threshold = rule.conditions.get('threshold', 0)
            
            if field in event.data:
                value = event.data[field]
                
                if isinstance(value, (int, float)):
                    if operator == 'greater_than' and value > threshold:
                        return self._create_threshold_match(rule, [event], field, value, threshold)
                    elif operator == 'less_than' and value < threshold:
                        return self._create_threshold_match(rule, [event], field, value, threshold)
                    elif operator == 'equals' and value == threshold:
                        return self._create_threshold_match(rule, [event], field, value, threshold)
                    elif operator == 'not_equals' and value != threshold:
                        return self._create_threshold_match(rule, [event], field, value, threshold)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking threshold pattern: {e}")
            return None
    
    def _create_threshold_match(self, rule: EventRule, events: List[StreamEvent], 
                              field: str, value: Any, threshold: Any) -> EventPatternMatch:
        """Create threshold pattern match"""
        return EventPatternMatch(
            pattern_id=rule.rule_id,
            pattern_type=EventPattern.THRESHOLD,
            matched_events=events,
            confidence=1.0,
            metadata={
                'field': field,
                'value': value,
                'threshold': threshold,
                'operator': rule.conditions.get('operator', 'greater_than')
            }
        )
    
    def _check_time_constraints(self, events: List[StreamEvent], max_time_gap_ms: int) -> bool:
        """Check if events satisfy time constraints"""
        if len(events) < 2:
            return True
        
        for i in range(1, len(events)):
            time_diff = (events[i].timestamp - events[i-1].timestamp).total_seconds() * 1000
            if time_diff > max_time_gap_ms:
                return False
        
        return True
    
    async def _execute_actions(self, rule: EventRule, match: EventPatternMatch):
        """Execute actions for matched pattern"""
        try:
            for action in rule.actions:
                action_type = action.get('type')
                
                if action_type == 'log':
                    self.logger.info(f"Pattern matched: {rule.name} - {match.metadata}")
                
                elif action_type == 'alert':
                    await self._send_alert(action, match)
                
                elif action_type == 'webhook':
                    await self._call_webhook(action, match)
                
                elif action_type == 'function':
                    await self._call_function(action, match)
                
                elif action_type == 'publish_event':
                    await self._publish_event(action, match)
                
        except Exception as e:
            self.logger.error(f"Error executing actions for rule {rule.rule_id}: {e}")
    
    async def _send_alert(self, action: Dict[str, Any], match: EventPatternMatch):
        """Send alert for pattern match"""
        # Implementation would depend on alert system
        self.logger.warning(f"ALERT: Pattern {match.pattern_id} matched with confidence {match.confidence}")
    
    async def _call_webhook(self, action: Dict[str, Any], match: EventPatternMatch):
        """Call webhook for pattern match"""
        import aiohttp
        
        url = action.get('url')
        method = action.get('method', 'POST')
        headers = action.get('headers', {})
        
        payload = {
            'pattern_id': match.pattern_id,
            'pattern_type': match.pattern_type.value,
            'confidence': match.confidence,
            'metadata': match.metadata,
            'timestamp': match.timestamp.isoformat(),
            'matched_events': [e.to_dict() for e in match.matched_events]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, json=payload, headers=headers) as response:
                    if response.status >= 400:
                        self.logger.error(f"Webhook failed: {response.status}")
        except Exception as e:
            self.logger.error(f"Webhook error: {e}")
    
    async def _call_function(self, action: Dict[str, Any], match: EventPatternMatch):
        """Call custom function for pattern match"""
        function_name = action.get('function')
        # Implementation would depend on function registry
        self.logger.info(f"Calling function: {function_name}")
    
    async def _publish_event(self, action: Dict[str, Any], match: EventPatternMatch):
        """Publish event for pattern match"""
        topic = action.get('topic', 'pattern_matches')
        
        # This would integrate with the stream processor
        self.logger.info(f"Publishing pattern match to topic: {topic}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processor statistics"""
        return {
            'total_rules': len(self.rules),
            'enabled_rules': sum(1 for rule in self.rules.values() if rule.enabled),
            'active_matches': len(self.active_matches),
            'event_counts': dict(self.event_counts),
            'sequence_states': {k: len(v) for k, v in self.sequence_states.items()},
            'frequency_counters': dict(self.frequency_counters)
        }

# Factory function
def create_complex_event_processor() -> ComplexEventProcessor:
    """Create complex event processor"""
    return ComplexEventProcessor()
