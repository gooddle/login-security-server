import resend

from app.core.config import settings


def send_new_ip_alert(to_email: str, ip_address: str) -> None:
    resend.api_key = settings.resend_api_key

    resend.Emails.send({
        "from": settings.email_from,
        "to": to_email,
        "subject": "[보안 알림] 새로운 위치에서 로그인 감지",
        "html": f"""
        <h2>새로운 IP에서 로그인이 감지되었습니다</h2>
        <p>IP 주소: <strong>{ip_address}</strong></p>
        <p>본인이 아닌 경우 즉시 비밀번호를 변경하세요.</p>
        """,
    })
