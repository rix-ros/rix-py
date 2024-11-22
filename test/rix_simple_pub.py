from rixcore.common import Protocol, get_local_ip, RIX_HUB_PORT
from rixcore.node import Node
from rixcore.publisher import Publisher
from rixmsg.standard.Time import Time

from time import time_ns, sleep

node = Node()
node.init('test', get_local_ip(), RIX_HUB_PORT)
pub = node.advertise(Time, 'test_topic', Protocol['TCP'])
node.spin(False)

while(node.ok()):
    t = Time()
    current_time = time_ns()
    t.sec = current_time // 1000000000
    t.nsec = current_time % 1000000000
    pub.publish(t)
    sleep(1)