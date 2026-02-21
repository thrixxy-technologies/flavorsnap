import { NextRequest } from 'next/server';

export interface LogEntry {
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  logger: string;
  message: string;
  module?: string;
  function?: string;
  line?: number;
  event_type?: string;
  [key: string]: any;
}

class StructuredLogger {
  private serviceName = 'flavorsnap-nextjs';

  private createLogEntry(
    level: LogEntry['level'],
    message: string,
    additionalData: Record<string, any> = {}
  ): LogEntry {
    return {
      timestamp: new Date().toISOString(),
      level,
      logger: this.serviceName,
      message,
      ...additionalData,
    };
  }

  private log(entry: LogEntry): void {
    // Log to console with appropriate level
    const logMessage = JSON.stringify(entry);
    
    switch (entry.level) {
      case 'DEBUG':
        console.debug(logMessage);
        break;
      case 'INFO':
        console.info(logMessage);
        break;
      case 'WARNING':
        console.warn(logMessage);
        break;
      case 'ERROR':
        console.error(logMessage);
        break;
      default:
        console.log(logMessage);
    }
  }

  debug(message: string, data: Record<string, any> = {}): void {
    this.log(this.createLogEntry('DEBUG', message, data));
  }

  info(message: string, data: Record<string, any> = {}): void {
    this.log(this.createLogEntry('INFO', message, data));
  }

  warning(message: string, data: Record<string, any> = {}): void {
    this.log(this.createLogEntry('WARNING', message, data));
  }

  error(message: string, data: Record<string, any> = {}): void {
    this.log(this.createLogEntry('ERROR', message, data));
  }

  logApiRequest(request: NextRequest, additionalData: Record<string, any> = {}): void {
    const headers: Record<string, string> = {};
    request.headers.forEach((value, key) => {
      headers[key] = value;
    });

    this.info(`API Request: ${request.method} ${request.url}`, {
      event_type: 'api_request',
      request_method: request.method,
      request_url: request.url,
      request_headers: headers,
      ...additionalData,
    });
  }

  logApiResponse(
    request: NextRequest,
    statusCode: number,
    responseBody: any = null,
    durationMs?: number,
    additionalData: Record<string, any> = {}
  ): void {
    this.info(`API Response: ${request.method} ${request.url} - ${statusCode}`, {
      event_type: 'api_response',
      request_method: request.method,
      request_url: request.url,
      response_status_code: statusCode,
      response_body: responseBody,
      response_duration_ms: durationMs,
      ...additionalData,
    });
  }

  logErrorWithTraceback(
    message: string,
    error: Error,
    additionalData: Record<string, any> = {}
  ): void {
    this.error(message, {
      event_type: 'error_with_traceback',
      exception_type: error.constructor.name,
      exception_message: error.message,
      exception_stack: error.stack,
      ...additionalData,
    });
  }
}

// Global logger instance
export const logger = new StructuredLogger();

// Middleware helper function
export function withLogging(handler: (req: NextRequest) => Promise<Response>) {
  return async (req: NextRequest): Promise<Response> => {
    const startTime = Date.now();
    
    try {
      logger.logApiRequest(req);
      
      const response = await handler(req);
      
      const duration = Date.now() - startTime;
      
      // Try to parse response body for logging
      let responseBody = null;
      try {
        const clonedResponse = response.clone();
        responseBody = await clonedResponse.json();
      } catch {
        // Response is not JSON, skip body logging
      }
      
      logger.logApiResponse(req, response.status, responseBody, duration);
      
      return response;
    } catch (error) {
      const duration = Date.now() - startTime;
      
      logger.logErrorWithTraceback(
        'Unhandled error in API route',
        error as Error,
        {
          request_method: req.method,
          request_url: req.url,
          response_duration_ms: duration,
        }
      );
      
      throw error;
    }
  };
}
