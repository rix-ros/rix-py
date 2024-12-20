from rixcore.common import Protocol, get_public_ip, RIX_HUB_PORT
from rixcore.node import Node
from rixcore.subscriber import Subscriber
from rixmsg.standard.Time import Time

def callback(msg: Time) -> None:
    print(f"Received: {msg.sec}.{msg.nsec}")

node = Node()
node.init('test', get_public_ip(), RIX_HUB_PORT)
sub = node.subscribe(Time, 'test_topic', callback, Protocol['TCP'])
node.spin()