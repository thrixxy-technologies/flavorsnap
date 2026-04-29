/**
 * Real-time Preview JavaScript Module
 * 
 * Provides client-side real-time updates, visual indicators, and smooth
 * transitions for the FlavorSnap real-time classification feature.
 */

class RealtimePreview {
    constructor() {
        this.isEnabled = true;
        this.debounceDelay = 300;
        this.pendingRequests = new Map();
        this.confidenceHistory = [];
        this.performanceMetrics = {
            totalRequests: 0,
            cacheHits: 0,
            averageResponseTime: 0,
            lastResponseTime: 0
        };
        
        this.initializeEventListeners();
        this.initializeVisualElements();
        this.setupWebSocketConnection();
    }

    /**
     * Initialize event listeners for preprocessing controls
     */
    initializeEventListeners() {
        // Listen for preprocessing control changes
        const controls = ['brightness', 'contrast', 'rotation', 'aspect_ratio'];
        
        controls.forEach(control => {
            const element = document.querySelector(`[data-control="${control}"]`);
            if (element) {
                element.addEventListener('input', this.debounceUpdate.bind(this));
                element.addEventListener('change', this.immediateUpdate.bind(this));
            }
        });

        // Listen for real-time toggle
        const realtimeToggle = document.querySelector('[data-action="toggle-realtime"]');
        if (realtimeToggle) {
            realtimeToggle.addEventListener('change', (e) => {
                this.isEnabled = e.target.checked;
                this.updateRealtimeStatus();
            });
        }

        // Listen for comparison mode changes
        const comparisonMode = document.querySelector('[data-control="comparison-mode"]');
        if (comparisonMode) {
            comparisonMode.addEventListener('change', (e) => {
                this.updateComparisonMode(e.target.value);
            });
        }
    }

    /**
     * Initialize visual elements and animations
     */
    initializeVisualElements() {
        // Create loading spinner overlay
        this.createLoadingOverlay();
        
        // Initialize confidence bar animations
        this.initializeConfidenceBar();
        
        // Setup before/after comparison slider
        this.initializeComparisonSlider();
        
        // Initialize status indicators
        this.initializeStatusIndicators();
    }

    /**
     * Setup WebSocket connection for real-time updates
     */
    setupWebSocketConnection() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/realtime`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('Real-time WebSocket connected');
                this.updateConnectionStatus('connected');
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleRealtimeUpdate(data);
            };
            
            this.websocket.onclose = () => {
                console.log('Real-time WebSocket disconnected');
                this.updateConnectionStatus('disconnected');
                // Attempt to reconnect after 3 seconds
                setTimeout(() => this.setupWebSocketConnection(), 3000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus('error');
            };
        } catch (error) {
            console.warn('WebSocket not available, falling back to HTTP polling');
            this.setupHttpPolling();
        }
    }

    /**
     * Fallback HTTP polling for real-time updates
     */
    setupHttpPolling() {
        this.pollingInterval = setInterval(() => {
            if (this.isEnabled && this.hasActiveImage()) {
                this.requestClassificationUpdate();
            }
        }, 1000);
    }

    /**
     * Debounced update handler for preprocessing changes
     */
    debounceUpdate(event) {
        if (!this.isEnabled) return;
        
        const control = event.target.dataset.control;
        const value = event.target.value;
        
        // Clear existing timeout for this control
        if (this.pendingRequests.has(control)) {
            clearTimeout(this.pendingRequests.get(control));
        }
        
        // Set new timeout
        const timeoutId = setTimeout(() => {
            this.requestClassificationUpdate();
        }, this.debounceDelay);
        
        this.pendingRequests.set(control, timeoutId);
        
        // Show immediate visual feedback
        this.showProcessingIndicator(control);
    }

    /**
     * Immediate update handler for final changes
     */
    immediateUpdate(event) {
        if (!this.isEnabled) return;
        
        // Clear any pending debounced requests
        this.pendingRequests.forEach(timeoutId => clearTimeout(timeoutId));
        this.pendingRequests.clear();
        
        this.requestClassificationUpdate();
    }

    /**
     * Request classification update from server
     */
    async requestClassificationUpdate() {
        const startTime = performance.now();
        
        try {
            // Get current preprocessing parameters
            const params = this.getCurrentPreprocessingParams();
            
            // Show loading state
            this.showLoadingState();
            
            // Send request to server
            const response = await fetch('/api/classify/realtime', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image_id: this.getCurrentImageId(),
                    preprocessing_params: params,
                    request_id: this.generateRequestId()
                })
            });
            
            const data = await response.json();
            const responseTime = performance.now() - startTime;
            
            // Update performance metrics
            this.updatePerformanceMetrics(responseTime, data.cached);
            
            // Handle the response
            this.handleClassificationResponse(data);
            
        } catch (error) {
            console.error('Classification update failed:', error);
            this.showErrorState('Classification update failed');
        } finally {
            this.hideLoadingState();
        }
    }

    /**
     * Handle real-time update from WebSocket
     */
    handleRealtimeUpdate(data) {
        if (data.type === 'classification_result') {
            this.handleClassificationResponse(data.payload);
        } else if (data.type === 'optimization_suggestion') {
            this.handleOptimizationSuggestion(data.payload);
        } else if (data.type === 'performance_update') {
            this.updatePerformanceDisplay(data.payload);
        }
    }

    /**
     * Handle classification response
     */
    handleClassificationResponse(data) {
        if (data.error) {
            this.showErrorState(data.error);
            return;
        }

        // Update confidence display
        this.updateConfidenceDisplay(data.confidence, data.predicted_class);
        
        // Update result display
        this.updateResultDisplay(data);
        
        // Update confidence history
        this.updateConfidenceHistory(data.confidence, data.predicted_class);
        
        // Update before/after images if available
        if (data.processed_image_url) {
            this.updateProcessedImage(data.processed_image_url);
        }
        
        // Show success animation
        this.showSuccessAnimation();
    }

    /**
     * Handle optimization suggestions
     */
    handleOptimizationSuggestion(suggestions) {
        const suggestionsContainer = document.querySelector('[data-container="suggestions"]');
        if (!suggestionsContainer) return;
        
        suggestionsContainer.innerHTML = '';
        
        if (suggestions.length === 0) {
            suggestionsContainer.innerHTML = '<p class="text-muted">No suggestions available</p>';
            return;
        }
        
        suggestions.forEach((suggestion, index) => {
            const suggestionElement = this.createSuggestionElement(suggestion, index);
            suggestionsContainer.appendChild(suggestionElement);
        });
        
        // Show auto-apply button if there are high-priority suggestions
        const highPriorityCount = suggestions.filter(s => s.priority === 'high').length;
        const autoApplyButton = document.querySelector('[data-action="auto-apply"]');
        if (autoApplyButton) {
            autoApplyButton.style.display = highPriorityCount > 0 ? 'block' : 'none';
        }
    }

    /**
     * Create suggestion element
     */
    createSuggestionElement(suggestion, index) {
        const element = document.createElement('div');
        element.className = `suggestion-item priority-${suggestion.priority}`;
        element.innerHTML = `
            <div class="suggestion-header">
                <span class="suggestion-type">${suggestion.type}</span>
                <span class="suggestion-impact">${suggestion.estimated_impact}</span>
            </div>
            <div class="suggestion-content">
                <p class="suggestion-reason">${suggestion.reason}</p>
                <div class="suggestion-actions">
                    <button class="btn btn-sm btn-primary" data-action="apply-suggestion" data-index="${index}">
                        Apply
                    </button>
                    <button class="btn btn-sm btn-light" data-action="dismiss-suggestion" data-index="${index}">
                        Dismiss
                    </button>
                </div>
            </div>
        `;
        
        // Add event listeners
        element.querySelector('[data-action="apply-suggestion"]').addEventListener('click', () => {
            this.applySuggestion(suggestion);
        });
        
        element.querySelector('[data-action="dismiss-suggestion"]').addEventListener('click', () => {
            element.style.display = 'none';
        });
        
        return element;
    }

    /**
     * Apply optimization suggestion
     */
    async applySuggestion(suggestion) {
        try {
            // Update the corresponding control
            const controlElement = document.querySelector(`[data-control="${suggestion.type}"]`);
            if (controlElement) {
                controlElement.value = suggestion.suggested_value;
                controlElement.dispatchEvent(new Event('input'));
                controlElement.dispatchEvent(new Event('change'));
            }
            
            // Show feedback
            this.showNotification(`Applied ${suggestion.type} optimization`, 'success');
            
        } catch (error) {
            console.error('Failed to apply suggestion:', error);
            this.showNotification('Failed to apply suggestion', 'error');
        }
    }

    /**
     * Update confidence display with animation
     */
    updateConfidenceDisplay(confidence, predictedClass) {
        const confidenceBar = document.querySelector('[data-element="confidence-bar"]');
        const confidenceText = document.querySelector('[data-element="confidence-text"]');
        
        if (confidenceBar) {
            const percentage = confidence * 100;
            confidenceBar.style.width = `${percentage}%`;
            
            // Update color based on confidence level
            if (confidence >= 0.8) {
                confidenceBar.className = 'confidence-bar high';
            } else if (confidence >= 0.6) {
                confidenceBar.className = 'confidence-bar medium';
            } else {
                confidenceBar.className = 'confidence-bar low';
            }
        }
        
        if (confidenceText) {
            const emoji = confidence >= 0.8 ? '🟢' : confidence >= 0.6 ? '🟡' : '🔴';
            confidenceText.innerHTML = `${emoji} <strong>${predictedClass}</strong>: ${(confidence * 100).toFixed(1)}%`;
        }
    }

    /**
     * Update result display
     */
    updateResultDisplay(data) {
        const resultElement = document.querySelector('[data-element="result-text"]');
        if (!resultElement) return;
        
        const confidenceChange = this.calculateConfidenceChange(data.confidence);
        const changeEmoji = confidenceChange > 0 ? '📈' : confidenceChange < 0 ? '📉' : '➡️';
        const changeText = confidenceChange !== 0 ? ` (${changeEmoji} ${(confidenceChange * 100).toFixed(1)}%)` : '';
        
        resultElement.innerHTML = `
            <strong>${data.predicted_class}</strong>${changeText}<br>
            <small>Confidence: ${(data.confidence * 100).toFixed(1)}%</small>
        `;
    }

    /**
     * Update confidence history
     */
    updateConfidenceHistory(confidence, predictedClass) {
        this.confidenceHistory.push({
            timestamp: Date.now(),
            confidence: confidence,
            predictedClass: predictedClass
        });
        
        // Keep only last 50 entries
        if (this.confidenceHistory.length > 50) {
            this.confidenceHistory = this.confidenceHistory.slice(-50);
        }
        
        // Update trend indicator
        this.updateTrendIndicator();
    }

    /**
     * Update trend indicator
     */
    updateTrendIndicator() {
        if (this.confidenceHistory.length < 2) return;
        
        const recent = this.confidenceHistory.slice(-10);
        const avgRecent = recent.reduce((sum, entry) => sum + entry.confidence, 0) / recent.length;
        
        let trend = '➡️ Stable';
        if (this.confidenceHistory.length >= 10) {
            const earlier = this.confidenceHistory.slice(-20, -10);
            const avgEarlier = earlier.reduce((sum, entry) => sum + entry.confidence, 0) / earlier.length;
            
            if (avgRecent > avgEarlier + 0.05) {
                trend = '📈 Improving';
            } else if (avgRecent < avgEarlier - 0.05) {
                trend = '📉 Declining';
            }
        }
        
        const trendElement = document.querySelector('[data-element="trend-indicator"]');
        if (trendElement) {
            trendElement.textContent = trend;
        }
    }

    /**
     * Update comparison mode
     */
    updateComparisonMode(mode) {
        const container = document.querySelector('[data-container="image-comparison"]');
        if (!container) return;
        
        // Remove all mode classes
        container.classList.remove('mode-side-by-side', 'mode-slider', 'mode-toggle');
        
        // Add new mode class
        container.classList.add(`mode-${mode}`);
        
        // Update visibility of comparison controls
        const slider = document.querySelector('[data-control="comparison-slider"]');
        if (slider) {
            slider.style.display = mode === 'slider' ? 'block' : 'none';
        }
    }

    /**
     * Create loading overlay
     */
    createLoadingOverlay() {
        const overlay = document.createElement('div');
        overlay.className = 'realtime-loading-overlay';
        overlay.innerHTML = `
            <div class="loading-spinner"></div>
            <div class="loading-text">Processing...</div>
        `;
        overlay.style.display = 'none';
        document.body.appendChild(overlay);
        
        this.loadingOverlay = overlay;
    }

    /**
     * Show loading state
     */
    showLoadingState() {
        if (this.loadingOverlay) {
            this.loadingOverlay.style.display = 'flex';
        }
        
        const statusIndicator = document.querySelector('[data-element="status-indicator"]');
        if (statusIndicator) {
            statusIndicator.className = 'status-indicator processing';
        }
    }

    /**
     * Hide loading state
     */
    hideLoadingState() {
        if (this.loadingOverlay) {
            this.loadingOverlay.style.display = 'none';
        }
        
        const statusIndicator = document.querySelector('[data-element="status-indicator"]');
        if (statusIndicator) {
            statusIndicator.className = 'status-indicator ready';
        }
    }

    /**
     * Show error state
     */
    showErrorState(message) {
        const errorElement = document.querySelector('[data-element="error-message"]');
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                errorElement.style.display = 'none';
            }, 5000);
        }
        
        const statusIndicator = document.querySelector('[data-element="status-indicator"]');
        if (statusIndicator) {
            statusIndicator.className = 'status-indicator error';
        }
    }

    /**
     * Show success animation
     */
    showSuccessAnimation() {
        const resultElement = document.querySelector('[data-element="result-text"]');
        if (resultElement) {
            resultElement.classList.add('success-animation');
            setTimeout(() => {
                resultElement.classList.remove('success-animation');
            }, 1000);
        }
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }

    /**
     * Get current preprocessing parameters
     */
    getCurrentPreprocessingParams() {
        const params = {};
        const controls = ['brightness', 'contrast', 'rotation', 'aspect_ratio'];
        
        controls.forEach(control => {
            const element = document.querySelector(`[data-control="${control}"]`);
            if (element) {
                params[control] = element.value;
            }
        });
        
        return params;
    }

    /**
     * Get current image ID
     */
    getCurrentImageId() {
        const imageElement = document.querySelector('[data-element="current-image"]');
        return imageElement ? imageElement.dataset.imageId : null;
    }

    /**
     * Check if there's an active image
     */
    hasActiveImage() {
        return this.getCurrentImageId() !== null;
    }

    /**
     * Generate unique request ID
     */
    generateRequestId() {
        return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Calculate confidence change
     */
    calculateConfidenceChange(currentConfidence) {
        if (this.confidenceHistory.length === 0) return 0;
        
        const lastConfidence = this.confidenceHistory[this.confidenceHistory.length - 1].confidence;
        return currentConfidence - lastConfidence;
    }

    /**
     * Update performance metrics
     */
    updatePerformanceMetrics(responseTime, cached) {
        this.performanceMetrics.totalRequests++;
        this.performanceMetrics.lastResponseTime = responseTime;
        
        if (cached) {
            this.performanceMetrics.cacheHits++;
        }
        
        // Update average response time
        const total = this.performanceMetrics.totalRequests;
        const current = this.performanceMetrics.averageResponseTime;
        this.performanceMetrics.averageResponseTime = (current * (total - 1) + responseTime) / total;
        
        this.updatePerformanceDisplay();
    }

    /**
     * Update performance display
     */
    updatePerformanceDisplay() {
        const performanceElement = document.querySelector('[data-element="performance-metrics"]');
        if (!performanceElement) return;
        
        const cacheHitRate = this.performanceMetrics.totalRequests > 0 
            ? (this.performanceMetrics.cacheHits / this.performanceMetrics.totalRequests * 100).toFixed(1)
            : 0;
        
        performanceElement.innerHTML = `
            <div>Cache Hit Rate: ${cacheHitRate}%</div>
            <div>Avg Response: ${this.performanceMetrics.averageResponseTime.toFixed(0)}ms</div>
            <div>Last Response: ${this.performanceMetrics.lastResponseTime.toFixed(0)}ms</div>
            <div>Total Requests: ${this.performanceMetrics.totalRequests}</div>
        `;
    }

    /**
     * Update connection status
     */
    updateConnectionStatus(status) {
        const statusElement = document.querySelector('[data-element="connection-status"]');
        if (statusElement) {
            statusElement.className = `connection-status ${status}`;
            statusElement.title = `Connection: ${status}`;
        }
    }

    /**
     * Update real-time status display
     */
    updateRealtimeStatus() {
        const statusText = document.querySelector('[data-element="realtime-status"]');
        if (statusText) {
            statusText.textContent = this.isEnabled ? 'Real-time: ON' : 'Real-time: OFF';
        }
    }

    /**
     * Initialize confidence bar animations
     */
    initializeConfidenceBar() {
        const style = document.createElement('style');
        style.textContent = `
            .confidence-bar {
                transition: width 0.3s ease-out, background-color 0.3s ease;
            }
            .confidence-bar.high { background-color: #28a745; }
            .confidence-bar.medium { background-color: #ffc107; }
            .confidence-bar.low { background-color: #dc3545; }
            
            .success-animation {
                animation: pulse 1s ease-in-out;
            }
            
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            
            .realtime-loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            }
            
            .loading-spinner {
                width: 40px;
                height: 40px;
                border: 4px solid #f3f3f3;
                border-top: 4px solid #007bff;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .loading-text {
                color: white;
                margin-top: 10px;
                font-weight: bold;
            }
            
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 12px 20px;
                border-radius: 4px;
                color: white;
                font-weight: bold;
                z-index: 10000;
                transform: translateX(100%);
                transition: transform 0.3s ease;
            }
            
            .notification.show {
                transform: translateX(0);
            }
            
            .notification-success { background-color: #28a745; }
            .notification-error { background-color: #dc3545; }
            .notification-info { background-color: #17a2b8; }
            
            .suggestion-item {
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-bottom: 10px;
                padding: 10px;
            }
            
            .suggestion-item.priority-high {
                border-left: 4px solid #dc3545;
            }
            
            .suggestion-item.priority-medium {
                border-left: 4px solid #ffc107;
            }
            
            .suggestion-item.priority-low {
                border-left: 4px solid #28a745;
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Initialize comparison slider
     */
    initializeComparisonSlider() {
        const slider = document.querySelector('[data-control="comparison-slider"]');
        if (!slider) return;
        
        slider.addEventListener('input', (e) => {
            const value = e.target.value;
            const originalImage = document.querySelector('.original-image');
            const processedImage = document.querySelector('.processed-image');
            
            if (value === 'before') {
                originalImage.style.display = 'block';
                processedImage.style.display = 'none';
            } else {
                originalImage.style.display = 'block';
                processedImage.style.display = 'block';
            }
        });
    }

    /**
     * Initialize status indicators
     */
    initializeStatusIndicators() {
        const style = document.createElement('style');
        style.textContent = `
            .status-indicator {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                display: inline-block;
                margin-right: 5px;
            }
            
            .status-indicator.ready { background-color: #28a745; }
            .status-indicator.processing { background-color: #ffc107; animation: pulse 1s infinite; }
            .status-indicator.error { background-color: #dc3545; }
            
            .connection-status {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                display: inline-block;
            }
            
            .connection-status.connected { background-color: #28a745; }
            .connection-status.disconnected { background-color: #dc3545; }
            .connection-status.error { background-color: #ffc107; }
        `;
        document.head.appendChild(style);
    }
}

// Initialize the real-time preview when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.realtimePreview = new RealtimePreview();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RealtimePreview;
}
