"""
Minimal API key auth, applied as a router-level dependency (see
app/routers/*.py: dependencies=[Depends(require_api_key)]).

Deliberately simple on purpose — a single shared secret in a header is
enough to stop casual/accidental public access to the demo without needing
a user/login system none of the 6 of you have time to build this week.
If judges ask "what about security", the honest answer is: shared API key
for the hackathon deployment, and here's exactly what a real auth layer
(OAuth2/JWT, per-user keys, rate limiting) would replace it with.
"""
from fastapi import Header, HTTPException, status

from app.config import API_KEY


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    if not API_KEY:
        # No key configured -> auth is off (local/dev mode). Matches the
        # existing "CORS_ORIGINS=*" wide-open-for-hackathon posture.
        return
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key. Send it as header: X-API-Key",
        )
