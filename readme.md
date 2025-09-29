# RIX-PY: Robotics Interprocess eXchange for Python

## Fast, Modular Interprocess Communication for Robotics

**RIX-PY** is a Python library for real-time interprocess communication in robotics and distributed systems. It delivers robust messaging, node management, and service orchestration—empowering you to build scalable, reliable robot software architectures in Python.

- 🚀 **Fast & Lightweight:** Minimal dependencies, optimized for low-latency and high-throughput.
- 🧩 **Modular:** Easily extendable with publishers, subscribers, services, and timers.
- 🤖 **Robotics-Ready:** Designed for modern robotics applications.
- 🔒 **Reliable:** TCP-based communication ensures message integrity; loosely-coupled nodes provide system stability across distributed environments.

RIX-PY makes it easy to develop complex robotic systems, offering a clean API and powerful tools for node registration, topic management, and service handling.

---

## Get Started: Build Scalable, Real-Time Robotic Applications with RIX-PY

### Installation

Run the install script to set up RIX-PY and its dependencies:

```bash
bash install.sh
```

This will:
- Copy the `rixcore` Python package to `$HOME/.rix/python/`
- Create a Python 3.12 virtual environment in `$HOME/.rix/venv/`
- Install `rixmsg` and `rixcore` in editable mode

**Note:** You need Python 3.12 installed and available in your PATH.

### Environment Setup

Before running any RIX-PY executable, source the setup script to set environment variables:

```bash
source ~/.rix/setup.bash
rixhub
```

You can add this to your `.bashrc` (or similar) for convenience:

```bash
echo 'source ~/.rix/setup.bash' >> ~/.bashrc
```

---

## Python API Tutorial

RIX-PY is organized into Nodes that communicate via message streams (topics) and remote procedural calls (services). Start the `rixhub` server before running your nodes.

### Publisher Example

Create a publisher that sends `Header` messages at 1 Hz:

```python
from rixcore.node import Node
from rix.msg.standard.Header import Header
from rixcore.timer import Timer
from time import time_ns

def timer_callback(event: Timer.Event):
    msg = Header()
    current_time = time_ns()
    msg.frame_id = "Hello, world!"
    msg.stamp.sec = current_time // 1000000000
    msg.stamp.nsec = current_time % 1000000000
    pub.publish(msg)

node = Node("publisher_node")
pub = node.create_publisher(Header, "/my_topic")
node.create_timer(1.0, timer_callback)
node.spin()
```

### Subscriber Example

Register a subscriber on the same topic:

```python
from rixcore.node import Node
from rix.msg.standard.Header import Header

def callback(msg: Header):
    print(f"Received: {msg.frame_id}, {msg.stamp.sec}.{msg.stamp.nsec}")

node = Node("subscriber_node")
node.create_subscriber(Header, "/my_topic", callback)
node.spin()
```

### Service Example

Provide a request-response service:

```python
from rixcore.node import Node
from rix.msg.standard.String import String
from rix.msg.standard.UInt32 import UInt32

def service_callback(req: UInt32, res: String):
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    res.data = alphabet[req.data % 26]

node = Node("service_node")
node.create_service(UInt32, String, "/alphabet", service_callback)
node.spin()
```

### Service Client Example

Call a service from another node:

```python
from rixcore.node import Node
from rix.msg.standard.String import String
from rix.msg.standard.UInt32 import UInt32

node = Node("service_client_node")
service_client = node.create_service_client(UInt32, String, "/alphabet")

req = UInt32()
req.data = 5
res = String()
if service_client.call(req, res):
    print(f"Response: {res.data}")
```

---

## Advanced: Video Streaming Example

RIX-PY supports streaming video frames using OpenCV. See [`test/video_pub.py`](test/video_pub.py) and [`test/video_sub.py`](test/video_sub.py) for full examples.

---

## Finding Your IP Address

If you do not have a static IP address, you can modify the `~/.rix/setup.bash` file to use your public IP address.

On Linux:
```bash
export RIX_DEFAULT_IP=$(hostname -I)
```

On MacOS:
```bash
export RIX_DEFAULT_IP=$(ipconfig getifaddr en0)
```

---

## More Information

- [RIX Message Documentation](https://github.com/rix-ros/rix-msg)
- [RIX C++ Documentation](https://github.com/rix-ros/rix-cpp)

---

## License

See [LICENSE.md](LICENSE.md) for details.

---