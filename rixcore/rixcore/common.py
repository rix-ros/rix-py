import socket
import errno

Protocol = {
    'TCP': 0x01,
    'UDP': 0x02,
    'SHM': 0x04,
    'WEB': 0x08,
    'WEB2': 0x10
}

CORE_TOPICS = {
    'PING': 70,
    'PONG': 71,
    'SUB_REGISTER': 80,
    'PUB_REGISTER': 81,
    'SRV_REGISTER': 82,
    'ACT_REGISTER': 83,
    'SUB_NOTIFY': 90,
    'PUB_NOTIFY': 91,
    'SRV_NOTIFY': 92,
    'ACT_NOTIFY': 93,
    'SUB_DEREGISTER': 100,
    'PUB_DEREGISTER': 101,
    'SRV_DEREGISTER': 102,
    'ACT_DEREGISTER': 103,
    'SUB_DISCONNECT': 110,
    'PUB_DISCONNECT': 111,
    'SRV_DISCONNECT': 112,
    'ACT_DISCONNECT': 113,
    'SUB_REQUEST': 120,
    'SUB_RESPONSE': 121,
    'PUB_RESPONSE': 130,
    'SRV_REQUEST': 140,
    'SRV_RESPONSE': 141,
    'ACT_REQUEST': 150,
    'ACT_RESPONSE': 151,
    'MED_TERMINATE': 160
}

CORE_ERROR_CODES = {
    'NO_ERROR': 0,
    'WRONG_MSG_TYPE': 1,
    'WRONG_REQ_TYPE': 2,
    'WRONG_RES_TYPE': 3,
    'WRONG_TOPIC': 4,
    'EMPTY_TOPIC': 5,
    'EMPTY_SRV': 6,
    'EMPTY_ACT': 7,
    'MULTICAST_EXISTS': 8,
    'SHMEM_EXISTS': 9,
    'PUB_EXISTS': 10,
    'SUB_EXISTS': 11,
    'SRV_EXISTS': 12,
    'SRV_NOT_FOUND': 13,
    'ACT_EXISTS': 14,
    'ACT_NOT_FOUND': 15
}

RIX_HUB_PORT = 8000

def get_public_ip() -> str:
    try:
        # Create a socket connection to an external server
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to a public DNS server (Google's DNS server)
        s.connect(("8.8.8.8", 80))
        # Get the IP address of the machine
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except Exception as e:
        return str(e)
    
def recv_all_bytes(sock, size: int, block: bool = False) -> bytes:
    data = b''
    while len(data) < size:
        try:
            packet = sock.recv(size - len(data))
            if not packet:
                # Connection closed
                return None
            data += packet
        except socket.timeout:
            if block:
                continue
            elif len(data) == 0:
                return None
            else:
                continue
        except socket.error as e:
            if len(data) == 0:
                if block:
                    continue
                return None
            elif len(data) > 0 and (e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK):
                continue
            return None
    return data

def send_all_bytes(sock, data: bytes) -> bool:
    total_sent = 0
    total_size = len(data)
    while total_sent < total_size:
        try:
            status = sock.send(data[total_sent:])
            total_sent += status
        except socket.error as e:
            if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                continue
            return False
    return True