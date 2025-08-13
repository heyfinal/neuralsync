import os, asyncio, websockets, json, ssl

HOST = os.getenv("NEURALSYNC_BUS_HOST","0.0.0.0")
PORT = int(os.getenv("NEURALSYNC_BUS_PORT","8765"))
ENTERPRISE = os.getenv("NEURALSYNC_ENTERPRISE","0") == "1"
CRT = os.getenv("NEURALSYNC_BUS_CRT","/etc/nsbus/neuralsync.crt")
KEY = os.getenv("NEURALSYNC_BUS_KEY","/etc/nsbus/neuralsync.key")

connected = {}  # name -> websocket

async def handler(ws):
    name = None
    try:
        reg = await ws.recv()
        j = json.loads(reg)
        name = j.get("name")
        if not name:
            await ws.close(); return
        connected[name] = ws
        print(f"[BUS] {name} connected")
        await ws.send(json.dumps({"from":"bus","message":"ACK"}))
        async for msg in ws:
            data = json.loads(msg)
            target = data.get("to")
            if target and target in connected:
                await connected[target].send(json.dumps({
                    "from": name,
                    "message": data.get("message"),
                    "meta": data.get("meta",{})
                }))
    except Exception as e:
        print("[BUS] error:", e)
    finally:
        if name and name in connected:
            del connected[name]
            print(f"[BUS] {name} disconnected")

async def main():
    if ENTERPRISE:
        os.makedirs("/etc/nsbus", exist_ok=True)
        ssl_ctx = None
        if os.path.exists(CRT) and os.path.exists(KEY):
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_ctx.load_cert_chain(CRT, KEY)
        async with websockets.serve(lambda ws, p: handler(ws), HOST, PORT, ssl=ssl_ctx):
            print(f"[BUS] WSS on wss://{HOST}:{PORT}")
            await asyncio.Future()
    else:
        async with websockets.serve(lambda ws, p: handler(ws), HOST, PORT):
            print(f"[BUS] WS on ws://{HOST}:{PORT}")
            await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
