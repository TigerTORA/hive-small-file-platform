import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict


class KerberosDiagnosticCode(str, Enum):
    """Unified diagnostic codes for Kerberos related failures."""

    TICKET_EXPIRED = "KERBEROS_TICKET_EXPIRED"
    KEYTAB_PERMISSION = "KERBEROS_KEYTAB_PERMISSION_DENIED"
    KEYTAB_MISSING = "KERBEROS_KEYTAB_NOT_FOUND"
    DNS_RESOLUTION_FAILED = "KERBEROS_DNS_RESOLUTION_FAILED"
    KDC_UNREACHABLE = "KERBEROS_KDC_UNREACHABLE"
    AUTHENTICATION_FAILED = "KERBEROS_AUTHENTICATION_FAILED"
    KINIT_FAILURE = "KERBEROS_KINIT_FAILURE"
    CONFIG_MISSING = "KERBEROS_CONFIGURATION_INCOMPLETE"
    UNKNOWN = "KERBEROS_UNKNOWN_ERROR"


@dataclass(frozen=True)
class KerberosDiagnostic:
    code: KerberosDiagnosticCode
    message: str
    recommended_action: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "diagnostic_code": self.code.value,
            "message": self.message,
            "recommended_action": self.recommended_action,
        }


class KerberosDiagnosticError(RuntimeError):
    """Exception that carries a Kerberos diagnostic."""

    def __init__(
        self,
        diagnostic: KerberosDiagnostic,
        *,
        original: Optional[Exception] = None,
    ):
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic
        self.original = original


def build_diagnostic(
    code: KerberosDiagnosticCode,
    *,
    detail: Optional[str] = None,
) -> KerberosDiagnostic:
    base_actions = {
        KerberosDiagnosticCode.TICKET_EXPIRED: "执行 `kinit -kt <keytab> <principal>` 重新获取票据，并确认 KDC 可访问。",
        KerberosDiagnosticCode.KEYTAB_PERMISSION: "检查 keytab 文件权限及所有者，确保服务账户具备读取权限。",
        KerberosDiagnosticCode.KEYTAB_MISSING: "确认 keytab 路径是否正确，文件是否部署到目标主机。",
        KerberosDiagnosticCode.DNS_RESOLUTION_FAILED: "检查 DNS 设置或 hosts 配置，保证 KDC/HiveServer2 主机名可解析。",
        KerberosDiagnosticCode.KDC_UNREACHABLE: "确认网络连通性和防火墙策略，确保客户端能访问 KDC 端口。",
        KerberosDiagnosticCode.AUTHENTICATION_FAILED: "核对 principal 与 keytab 是否匹配，确保服务主体已在 KDC 注册。",
        KerberosDiagnosticCode.KINIT_FAILURE: "查看 kinit 输出的错误信息，确认 keytab/principal 与 KDC 状态正常。",
        KerberosDiagnosticCode.CONFIG_MISSING: "补全 Kerberos 配置：principal、keytab、realm 等必填项。",
        KerberosDiagnosticCode.UNKNOWN: "查看服务日志与 Kerberos 客户端日志，获取更多错误详情。",
    }

    message = detail or {
        KerberosDiagnosticCode.TICKET_EXPIRED: "Kerberos 票据已过期。",
        KerberosDiagnosticCode.KEYTAB_PERMISSION: "Keytab 文件权限不足。",
        KerberosDiagnosticCode.KEYTAB_MISSING: "未找到指定的 keytab 文件。",
        KerberosDiagnosticCode.DNS_RESOLUTION_FAILED: "DNS 解析失败。",
        KerberosDiagnosticCode.KDC_UNREACHABLE: "无法连接到 KDC。",
        KerberosDiagnosticCode.AUTHENTICATION_FAILED: "Kerberos 认证失败。",
        KerberosDiagnosticCode.KINIT_FAILURE: "执行 kinit 命令失败。",
        KerberosDiagnosticCode.CONFIG_MISSING: "Kerberos 配置不完整。",
        KerberosDiagnosticCode.UNKNOWN: "发生未知的 Kerberos 错误。",
    }[code]

    action = base_actions.get(code, base_actions[KerberosDiagnosticCode.UNKNOWN])
    return KerberosDiagnostic(code=code, message=message, recommended_action=action)


def map_exception_to_diagnostic(error: Exception) -> KerberosDiagnostic:
    """Best-effort mapping from an exception to a diagnostic."""
    err = str(error).lower()
    if "ticket" in err and "expire" in err:
        return build_diagnostic(KerberosDiagnosticCode.TICKET_EXPIRED, detail=str(error))
    if "permission" in err or "access denied" in err:
        return build_diagnostic(
            KerberosDiagnosticCode.KEYTAB_PERMISSION, detail=str(error)
        )
    if "no such file" in err or "not found" in err:
        return build_diagnostic(KerberosDiagnosticCode.KEYTAB_MISSING, detail=str(error))
    if "getaddrinfo" in err or "name or service not known" in err:
        return build_diagnostic(
            KerberosDiagnosticCode.DNS_RESOLUTION_FAILED, detail=str(error)
        )
    if "cannot contact any kdc" in err or "kdc" in err and "unreachable" in err:
        return build_diagnostic(KerberosDiagnosticCode.KDC_UNREACHABLE, detail=str(error))
    if "preauth failed" in err or "authentication" in err:
        return build_diagnostic(
            KerberosDiagnosticCode.AUTHENTICATION_FAILED, detail=str(error)
        )
    if "kinit" in err:
        return build_diagnostic(KerberosDiagnosticCode.KINIT_FAILURE, detail=str(error))
    return build_diagnostic(KerberosDiagnosticCode.UNKNOWN, detail=str(error))


def log_kerberos_diagnostic(
    logger: logging.Logger,
    level: str,
    diagnostic: KerberosDiagnostic,
    *,
    extra_context: Optional[dict] = None,
) -> None:
    """Log a Kerberos diagnostic with consistent format."""
    message = (
        f"[{diagnostic.code}] {diagnostic.message} "
        f"(Action: {diagnostic.recommended_action})"
    )
    ctx = extra_context or {}
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(message, extra={"diagnostic_code": diagnostic.code.value, **ctx})


def raise_diagnostic_error(
    code: KerberosDiagnosticCode,
    *,
    detail: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> None:
    diagnostic = build_diagnostic(code, detail=detail)
    if logger is not None:
        log_kerberos_diagnostic(logger, "error", diagnostic)
    raise KerberosDiagnosticError(diagnostic)
