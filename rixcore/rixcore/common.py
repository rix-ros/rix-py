import socket
from enum import IntEnum

from rixmsg.mediator.Operation import Operation
from rixmsg.mediator.Status import Status
from rixmsg.standard.UInt32 import UInt32
from rixmsg.message import Message

RIXHUB_PORT = 48104
MACHINE_ID_FILE = "~/.rix/machine_id"

class OPCODE(IntEnum):
    NODE_REGISTER = 80
    SUB_REGISTER = 81
    PUB_REGISTER = 82
    SRV_REGISTER = 83
    ACT_REGISTER = 84

    SUB_NOTIFY = 90

    NODE_DEREGISTER = 100
    SUB_DEREGISTER = 101
    PUB_DEREGISTER = 102
    SRV_DEREGISTER = 103
    ACT_DEREGISTER = 104

    SRV_REQUEST = 140
    ACT_REQUEST = 141
    PARAM_SET_REQUEST = 142
    PARAM_GET_REQUEST = 143
    SYSTEM_GET_REQUEST = 144

    SRV_RESPONSE = 150
    ACT_RESPONSE = 151
    TERMINATE = 160


def send_message_with_opcode_no_response(
    client: socket.socket, msg: Message, opcode: int
) -> bool:
    op = Operation()
    op.opcode = opcode
    op.len = msg.size()
    buffer = bytearray()
    op.serialize(buffer)
    msg.serialize(buffer)
    try:
        client.send(buffer)
    except Exception as _:
        return False
    return True


def send_message_with_opcode(
    client: socket.socket, msg: Message, opcode: int
) -> bool:
    if not send_message_with_opcode_no_response(client, msg, opcode):
        return False

    status = Status()
    msgLen = status.size()
    msgBuffer = bytearray(msgLen)
    client.recv_into(memoryview(msgBuffer), msgLen)
    status.deserialize(msgBuffer, Message.Offset())
    if status.error != 0:
        return False
    return True

def send_message_with_opcode_and_response(
    client: socket.socket, in_msg: Message, out_msg: Message, opcode: int
) -> bool:
    if not send_message_with_opcode_no_response(client, in_msg, opcode):
        return False

    sizeMsg = UInt32()
    msgLen = sizeMsg.size()
    msgBuffer = bytearray(msgLen)
    client.recv_into(memoryview(msgBuffer), msgLen)
    sizeMsg.deserialize(msgBuffer, Message.Offset())
    
    msgBuffer = bytearray(sizeMsg.data)
    client.recv_into(memoryview(msgBuffer), sizeMsg.data)
    out_msg.deserialize(msgBuffer, Message.Offset())
    return True

def send_opcode_with_response(
    client: socket.socket, out_msg: Message, opcode: int
) -> bool:
    op = Operation()
    op.opcode = opcode
    op.len = 0
    buffer = bytearray()
    op.serialize(buffer)
    try:
        client.send(buffer)
    except Exception as _:
        return False
    
    sizeMsg = UInt32()
    msgLen = sizeMsg.size()
    msgBuffer = bytearray(msgLen)
    client.recv_into(memoryview(msgBuffer), msgLen)
    sizeMsg.deserialize(msgBuffer, Message.Offset())
    
    msgBuffer = bytearray(sizeMsg.data)
    client.recv_into(memoryview(msgBuffer), sizeMsg.data)
    out_msg.deserialize(msgBuffer, Message.Offset())

    return True

