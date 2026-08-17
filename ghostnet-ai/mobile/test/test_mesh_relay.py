import socket
import json
import time

def test_mesh_relay_loopback():
    PORT = 8765
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', PORT))
    server.listen(1)
    server.settimeout(3.0)

    print(f"[TestMesh] Server listening on 127.0.0.1:{PORT}")

    # Simulated Device A broadcasting offline SOS
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('127.0.0.1', PORT))

    payload = {
        "device_id": "99999999-8888-7777-6666-555555555555",
        "lat": 23.1950,
        "lon": 86.0468,
        "category": "medical",
        "message": "SIMULATED MESH TEST: Hiker injured on remote trail.",
        "is_relayed": True,
    }

    client.sendall(json.dumps(payload).encode('utf-8'))
    client.close()

    # Simulated Device B receiving relay packet
    conn, addr = server.accept()
    data = conn.recv(4096)
    received_payload = json.loads(data.decode('utf-8'))
    conn.close()
    server.close()

    print("[TestMesh] Received relayed packet successfully:")
    print(received_payload)

    assert received_payload["is_relayed"] is True
    assert received_payload["category"] == "medical"
    print("Simulated Mesh Relay loopback test passed with zero errors!")

if __name__ == "__main__":
    test_mesh_relay_loopback()
