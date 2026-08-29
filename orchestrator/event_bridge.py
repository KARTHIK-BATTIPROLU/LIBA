import asyncio, json, logging, threading
logger = logging.getLogger('LIBA.EventBridge')
_loop = None
_connected_clients = set()
_bridge_ready = threading.Event()

async def _handler(websocket):
    _connected_clients.add(websocket)
    try:
        async for _ in websocket:
            pass
    except Exception:
        pass
    finally:
        _connected_clients.discard(websocket)

async def _broadcast(payload):
    dead = set()
    for ws in list(_connected_clients):
        try:
            await ws.send(payload)
        except Exception:
            dead.add(ws)
    _connected_clients.difference_update(dead)

async def _run_server(host, port):
    global _bridge_ready
    import websockets
    async with websockets.serve(_handler, host, port):
        _bridge_ready.set()
        logger.info('[EventBridge] Listening on ws://%s:%s', host, port)
        await asyncio.Future()

def _run_loop(host, port):
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    try:
        _loop.run_until_complete(_run_server(host, port))
    except Exception as exc:
        logger.error('[EventBridge] Server error: %s', exc)
    finally:
        _loop.close()

def start_bridge(host='localhost', port=8766, timeout=10.0):
    t = threading.Thread(target=_run_loop, args=(host, port), daemon=True, name='LIBAEventBridge')
    t.start()
    ready = _bridge_ready.wait(timeout=timeout)
    if not ready:
        logger.warning('[EventBridge] Server did not start in time.')
    return ready

def send_event(event_name):
    if _loop is None or _loop.is_closed():
        return
    payload = json.dumps({'event': event_name})
    try:
        asyncio.run_coroutine_threadsafe(_broadcast(payload), _loop)
        logger.debug('[EventBridge] Sent: %s', event_name)
    except Exception as exc:
        logger.warning('[EventBridge] Send failed %r: %s', event_name, exc)

if __name__ == '__main__':
    import time
    logging.basicConfig(level=logging.INFO)
    print('=== LIBA Event Bridge Standalone Test ===')
    ok = start_bridge()
    if not ok:
        print('FAIL: Bridge did not start.')
        raise SystemExit(1)
    print('PASS: Bridge running on ws://localhost:8766')
    print('Sending test events every 2s. Ctrl+C to stop.')
    events = ['listening', 'thinking', 'speaking', 'executing', 'idle', 'error', 'sleeping']
    idx = 0
    try:
        while True:
            evt = events[idx % len(events)]
            send_event(evt)
            print('  >> Sent:', evt)
            idx += 1
            time.sleep(2)
    except KeyboardInterrupt:
        print('Stopped.')