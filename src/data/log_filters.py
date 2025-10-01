from typing import Iterable, List, Callable
import re


def drop_health_checks(lines: Iterable[str]) -> List[str]:
    patterns = [
        re.compile(r"/healthz"),
        re.compile(r"/readyz"),
        re.compile(r"ELB-HealthChecker"),
    ]
    out: List[str] = []
    for line in lines:
        if any(p.search(line) for p in patterns):
            continue
        out.append(line)
    return out


def drop_noise_levels(lines: Iterable[str]) -> List[str]:
    # Remove very chatty INFO/DEBUG lines without error keywords
    noise = re.compile(r"\b(INFO|DEBUG)\b", re.I)
    errorish = re.compile(r"\b(ERROR|WARN|CRITICAL|FAIL|EXCEPTION)\b", re.I)
    out: List[str] = []
    for line in lines:
        if noise.search(line) and not errorish.search(line):
            continue
        out.append(line)
    return out


def redact_secrets(lines: Iterable[str]) -> List[str]:
    # Simple redactions for tokens, passwords
    patterns = [
        (re.compile(r"(password\s*[:=]\s*)([^\s]+)", re.I), r"\1[REDACTED]"),
        (re.compile(r"(api[_-]?key\s*[:=]\s*)([^\s]+)", re.I), r"\1[REDACTED]"),
        (re.compile(r"(Authorization: Bearer)\s+([^\s]+)", re.I), r"\1 [REDACTED]"),
    ]
    out: List[str] = []
    for line in lines:
        red = line
        for pattern, repl in patterns:
            red = pattern.sub(repl, red)
        out.append(red)
    return out


def apply_filters(lines: Iterable[str], filters: List[Callable[[Iterable[str]], List[str]]]) -> List[str]:
    out = list(lines)
    for f in filters:
        out = f(out)
    return out




