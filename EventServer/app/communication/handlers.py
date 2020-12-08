import json
from .handlers_core import ws_handler

TOKEN_KEY = 'token'


@ws_handler(command='auth', authorized=False)
async def authorize(data, ws=None, app=None, **kwargs):
    token = data.get(TOKEN_KEY)
    is_authorized = app['auth_backend'].validate(token)
    ws.authorized = is_authorized
    if is_authorized:
        ws.token = token
    await ws.send_str(json.dumps(dict(status=is_authorized, **data)))


@ws_handler(command='subscribe', authorized=False)
async def subscribe(data, app=None, ws=None, **ctx):
    bus = app['message_bus']
    hub_id = data['hubId']
    bus.subscribe(ws, hub_id)
    await ws.send_str(json.dumps(dict(command='subscribe', **data)))
