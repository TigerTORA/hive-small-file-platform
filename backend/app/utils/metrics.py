import threading
from collections import Counter
from typing import Dict

_lock = threading.Lock()
_kerberos_failure_counter = Counter()
_kerberos_ticket_events = Counter()


def increment_kerberos_failure(code: str) -> None:
    with _lock:
        _kerberos_failure_counter[code] += 1


def increment_ticket_event(event: str) -> None:
    with _lock:
        _kerberos_ticket_events[event] += 1


def snapshot_metrics() -> Dict[str, Dict[str, int]]:
    with _lock:
        return {
            "kerberos_failures": dict(_kerberos_failure_counter),
            "kerberos_ticket_events": dict(_kerberos_ticket_events),
        }


def reset_metrics() -> None:
    with _lock:
        _kerberos_failure_counter.clear()
        _kerberos_ticket_events.clear()
