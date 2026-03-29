from app.model.base import XrayModel

class VeePeeNET(XrayModel):
    host: str
    namespace: str
    name: str | None = None
