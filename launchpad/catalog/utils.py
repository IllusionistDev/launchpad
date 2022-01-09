import base64

__all__ = ['base64_encode']


def base64_encode(secret: str):
    return base64.b64encode(secret.encode('utf-8')).decode('utf-8')
