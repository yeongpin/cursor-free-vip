

import os
import sys
import logging
import traceback
import json
import time
from typing import Optional, Dict, Any, Callable, List, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import threading
from contextlib import contextmanager

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    CONFIGURATION = "configuration"
    NETWORK = "network"
    PROCESS = "process"
    FILE_SYSTEM = "file_system"
    PERMISSION = "permission"
    VALIDATION = "validation"
    BROWSER = "browser"
    AUTHENTICATION = "authentication"
    SYSTEM = "system"
    UNKNOWN = "unknown"

@dataclass
class ErrorInfo:
    timestamp: float
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    exception: Optional[Exception] = None
    traceback: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    user_action: Optional[str] = None
    resolved: bool = False
    resolution_time: Optional[float] = None

class ErrorRecoveryStrategy:
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_counts = {}
    
    def should_retry(self, error_info: ErrorInfo) -> bool:
        """Determine if operation should be retried"""
        error_key = f"{error_info.category.value}_{error_info.message}"
        current_retries = self.retry_counts.get(error_key, 0)
        
        if current_retries >= self.max_retries:
            return False
        
        # Don't retry critical errors
        if error_info.severity == ErrorSeverity.CRITICAL:
            return False
        
        # Don't retry permission errors
        if error_info.category == ErrorCategory.PERMISSION:
            return False
        
        return True
    
    def get_retry_delay(self, error_info: ErrorInfo) -> float:
        """Get delay before next retry"""
        error_key = f"{error_info.category.value}_{error_info.message}"
        current_retries = self.retry_counts.get(error_key, 0)
        return (self.backoff_factor ** current_retries)
    
    def record_retry(self, error_info: ErrorInfo) -> None:
        """Record a retry attempt"""
        error_key = f"{error_info.category.value}_{error_info.message}"
        self.retry_counts[error_key] = self.retry_counts.get(error_key, 0) + 1

class EnhancedErrorHandler:
    """Enhanced error handler with logging, categorization, and recovery"""
    
    def __init__(self, log_file: Optional[str] = None, enable_recovery: bool = True):
        self.log_file = log_file or "cursor_free_vip_errors.log"
        self.enable_recovery = enable_recovery
        self.recovery_strategy = ErrorRecoveryStrategy()
        self.error_history: List[ErrorInfo] = []
        self.error_callbacks: Dict[ErrorCategory, List[Callable]] = {}
        self._setup_logging()
        self._lock = threading.Lock()
    
    def _setup_logging(self) -> None:
        """Setup enhanced logging"""
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(self.log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # Configure file handler
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Configure console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Configure logger
        self.logger = logging.getLogger('CursorFreeVIP.ErrorHandler')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def categorize_error(self, exception: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorCategory:
        """Categorize error based on exception type and context"""
        exception_type = type(exception).__name__
        exception_message = str(exception).lower()
        
        # Network errors
        if any(keyword in exception_message for keyword in ['connection', 'timeout', 'network', 'http', 'url']):
            return ErrorCategory.NETWORK
        
        # File system errors
        if any(keyword in exception_message for keyword in ['file', 'directory', 'path', 'not found', 'permission']):
            if 'permission' in exception_message:
                return ErrorCategory.PERMISSION
            return ErrorCategory.FILE_SYSTEM
        
        # Process errors
        if any(keyword in exception_message for keyword in ['process', 'pid', 'terminate', 'kill']):
            return ErrorCategory.PROCESS
        
        # Browser errors
        if any(keyword in exception_message for keyword in ['browser', 'driver', 'selenium', 'chrome', 'firefox']):
            return ErrorCategory.BROWSER
        
        # Authentication errors
        if any(keyword in exception_message for keyword in ['auth', 'login', 'token', 'credential']):
            return ErrorCategory.AUTHENTICATION
        
        # Configuration errors
        if any(keyword in exception_message for keyword in ['config', 'setting', 'parameter']):
            return ErrorCategory.CONFIGURATION
        
        # Validation errors
        if any(keyword in exception_message for keyword in ['validation', 'invalid', 'format']):
            return ErrorCategory.VALIDATION
        
        # System errors
        if any(keyword in exception_message for keyword in ['system', 'os', 'platform']):
            return ErrorCategory.SYSTEM
        
        return ErrorCategory.UNKNOWN
    
    def determine_severity(self, exception: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity"""
        exception_message = str(exception).lower()
        
        # Critical errors
        if any(keyword in exception_message for keyword in ['fatal', 'critical', 'corrupt', 'broken']):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if category in [ErrorCategory.PERMISSION, ErrorCategory.AUTHENTICATION]:
            return ErrorSeverity.HIGH
        
        if any(keyword in exception_message for keyword in ['access denied', 'unauthorized', 'forbidden']):
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if category in [ErrorCategory.NETWORK, ErrorCategory.FILE_SYSTEM, ErrorCategory.PROCESS]:
            return ErrorSeverity.MEDIUM
        
        # Low severity errors
        if category in [ErrorCategory.VALIDATION, ErrorCategory.CONFIGURATION]:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    def handle_error(self, exception: Exception, context: Optional[Dict[str, Any]] = None, 
                    user_action: Optional[str] = None) -> ErrorInfo:
        with self._lock:
            category = self.categorize_error(exception, context)
            severity = self.determine_severity(exception, category)
            error_info = ErrorInfo(
                timestamp=time.time(),
                category=category,
                severity=severity,
                message=str(exception),
                exception=exception,
                traceback=traceback.format_exc(),
                context=context or {},
                user_action=user_action
            )
            
            self._log_error(error_info)
            
            self.error_history.append(error_info)
            
            self._execute_callbacks(error_info)
            
            if self.enable_recovery:
                self._attempt_recovery(error_info)
            
            return error_info
    
    def _log_error(self, error_info: ErrorInfo) -> None:
        log_message = f"""
Error Details:
- Category: {error_info.category.value}
- Severity: {error_info.severity.value}
- Message: {error_info.message}
- Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(error_info.timestamp))}
- User Action: {error_info.user_action or 'N/A'}
- Context: {json.dumps(error_info.context, indent=2)}
"""
        
        if error_info.traceback:
            log_message += f"\nTraceback:\n{error_info.traceback}"
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def _execute_callbacks(self, error_info: ErrorInfo) -> None:
        callbacks = self.error_callbacks.get(error_info.category, [])
        for callback in callbacks:
            try:
                callback(error_info)
            except Exception as e:
                self.logger.error(f"Error in callback: {e}")
    
    def _attempt_recovery(self, error_info: ErrorInfo) -> None:
        if not self.recovery_strategy.should_retry(error_info):
            return
        
        delay = self.recovery_strategy.get_retry_delay(error_info)
        self.logger.info(f"Attempting recovery in {delay:.2f} seconds...")
        
        self.recovery_strategy.record_retry(error_info)
        
        threading.Timer(delay, self._retry_operation, args=[error_info]).start()
    
    def _retry_operation(self, error_info: ErrorInfo) -> None:
        self.logger.info(f"Retrying operation for error: {error_info.message}")
    
    def register_callback(self, category: ErrorCategory, callback: Callable[[ErrorInfo], None]) -> None:
        if category not in self.error_callbacks:
            self.error_callbacks[category] = []
        self.error_callbacks[category].append(callback)
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        cutoff_time = time.time() - (hours * 3600)
        recent_errors = [e for e in self.error_history if e.timestamp >= cutoff_time]
        
        summary = {
            'total_errors': len(recent_errors),
            'by_category': {},
            'by_severity': {},
            'most_common': [],
            'unresolved': len([e for e in recent_errors if not e.resolved])
        }
        
        for error in recent_errors:
            category = error.category.value
            severity = error.severity.value
            
            summary['by_category'][category] = summary['by_category'].get(category, 0) + 1
            summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1
        
        error_messages = [e.message for e in recent_errors]
        from collections import Counter
        message_counts = Counter(error_messages)
        summary['most_common'] = message_counts.most_common(5)
        
        return summary
    
    def resolve_error(self, error_info: ErrorInfo, resolution: str) -> None:
        error_info.resolved = True
        error_info.resolution_time = time.time()
        error_info.user_action = resolution
        
        self.logger.info(f"Error resolved: {error_info.message} - Resolution: {resolution}")
    
    def clear_history(self, older_than_hours: int = 168) -> None:
        cutoff_time = time.time() - (older_than_hours * 3600)
        with self._lock:
            self.error_history = [e for e in self.error_history if e.timestamp >= cutoff_time]
        
        self.logger.info(f"Cleared error history older than {older_than_hours} hours")

@contextmanager
def error_context(handler: EnhancedErrorHandler, context: Optional[Dict[str, Any]] = None, 
                 user_action: Optional[str] = None):
    try:
        yield
    except Exception as e:
        handler.handle_error(e, context, user_action)
        raise

error_handler = EnhancedErrorHandler()

def handle_error(exception: Exception, context: Optional[Dict[str, Any]] = None, 
                user_action: Optional[str] = None) -> ErrorInfo:
    return error_handler.handle_error(exception, context, user_action)

def safe_execute(func: Callable, *args, context: Optional[Dict[str, Any]] = None, 
                user_action: Optional[str] = None, **kwargs) -> Any:
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_handler.handle_error(e, context, user_action)
        raise

def retry_on_error(func: Callable, max_retries: int = 3, *args, 
                  context: Optional[Dict[str, Any]] = None, user_action: Optional[str] = None, **kwargs) -> Any:
    last_exception: Optional[Exception] = None
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            error_info = error_handler.handle_error(e, context, user_action)
            
            if attempt < max_retries - 1:
                delay = 2 ** attempt
                time.sleep(delay)
                continue
            else:
                break
    
    if last_exception is not None:
        raise last_exception
    else:
        raise RuntimeError("Unexpected error in retry_on_error") 