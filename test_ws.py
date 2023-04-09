import json
import websocket


def echo(ws, msg):
    print(f"> {msg}")
    ws.send(json.dumps(msg))
    print(f"< {ws.recv()}")


if __name__ == "__main__":
    ws = websocket.WebSocket()
    ws.connect("ws://localhost:18521/ws")

    echo(ws, {"type": "/api/ws/test", "message": "Hello World"})
