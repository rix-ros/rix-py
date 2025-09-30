from rix.core import Node
from rix.msg.geometry import TF, TransformStamped

class TransformBroadcaster:
    def __init__(self, node: Node):
        self.node = node
        self.pub = node.create_publisher(TF, "/tf")

    def send_transform(self, transform: TransformStamped) -> None:
        tf = TF()
        tf.transforms = [transform]
        self.pub.publish(tf)

    def send_transforms(self, tf: TF) -> None:
        self.pub.publish(tf)