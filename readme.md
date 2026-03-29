# RIX-PY: Robotics Interprocess eXchange for Python

## Fast, Modular Interprocess Communication for Robotics

**RIX-PY** is a Python library for real-time interprocess communication in robotics and distributed systems. It delivers robust messaging, node management, and service orchestration—empowering you to build scalable, reliable robot software architectures in Python.

- 🚀 **Fast & Lightweight:** Minimal dependencies, optimized for low-latency and high-throughput.
- 🧩 **Modular:** Easily extendable with publishers, subscribers, services, and timers.
- 🤖 **Robotics-Ready:** Designed for modern robotics applications.
- 🔒 **Reliable:** TCP-based communication ensures message integrity; loosely-coupled nodes provide system stability across distributed environments.

### Support for Robotics Applications
- 🌳 **Transformation Trees:** Built-in support for 3D spatial transform trees (`rix/tf`), including frame graph management, transform broadcasting/listening, and time-based interpolation.
- 🦾 **Robot Model & Kinematics:** Parse robot descriptions from JSON (JRDF), manage kinematic chains, and perform forward/inverse kinematics with the `rix/rob` module.

RIX-PY makes it easy to develop complex robotic systems, offering a clean API and powerful tools for node registration, topic management, and service handling.

---

## Get Started: Build Scalable, Real-Time Robotic Applications with RIX-PY

### Installation

Run the install script to set up RIX-PY and its dependencies:

```bash
bash install.sh
```

This will:
- Copy the `rix` Python package to `$HOME/.rix/python/`
- Create a Python 3.12 virtual environment in `$HOME/.rix/venv/`
- Install `rix` in editable mode

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

### Timer Example
Create a node with a timer that prints a message every second:

```python
from rix.core import Node, Timer
def timer_callback(event: Timer.Event):
    print("Timer triggered!")

node = Node("timer_node")
node.create_timer(1.0, timer_callback)
node.spin()
```

### Publisher Example

Create a publisher that sends `Header` messages at 1 Hz:

```python
from rix.core import Node, Timer
from rix.std_msgs import Header
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
from rix.core import Node
from rix.std_msgs import Header

def callback(msg: Header):
    print(f"{msg.frame_id}, {msg.seq}")

node = Node("subscriber_node")
node.create_subscriber(Header, "/my_topic", callback)
node.spin()
```

### Service Example

Provide a request-response service:

```python
from rix.core import Node
from rix.std_msgs import Header, UInt32

def service_callback(req: UInt32, res: Header):
    print(f"Received request: {req.data}")
    res.frame_id = "Hello from service!"
    res.seq = req.data
    return

node = Node("service_node")
node.create_service(UInt32, Header, "/my_service", service_callback)
node.spin()
```

### Service Client Example

Call a service from another node:

```python
from rix.core import Node
from rix.std_msgs import Header, UInt32

node = Node("service_client_node")
service_client = node.create_service_client(UInt32, Header, "/my_service")

req = UInt32()
req.data = 5
res = Header()
if service_client.call(req, res):
    print(f"Response: {res.frame_id}, {res.seq}")
```

### Action Example

Create an action server that counts to a goal number:

```python
from rix.core import Node
from rix.std_msgs import UInt32, Header

count = 0

def action_callback(goal: UInt32, feedback: UInt32, result: Header):
    global count
    count += 1
    if count < goal.data:
        feedback.data = count
        return False
    result.frame_id = "Action completed!"
    result.seq = count
    count = 0
    return True

node = Node("action_node")
node.create_action(UInt32, Header, Header, "/my_action", action_callback)
node.spin()
```

### Action Client Example
Dispatch a goal to the action server:

```python
from rix.core import Node, Timer
from rix.std_msgs import UInt32, Header

node = Node("action_client_node")
action_client = node.create_action_client(UInt32, Header, Header, "/my_action")

def timer_callback(event: Timer.Event):
    global action_client
    goal = UInt32()
    goal.data = 5
    action_client.dispatch(goal)

node.create_timer(1.0, timer_callback)
node.spin()
```

## Advanced: Video Streaming Example

RIX-PY supports streaming video frames using OpenCV. See [`test/video_pub.py`](test/video_pub.py) and [`test/video_sub.py`](test/video_sub.py) for full examples.

---

## Finding Your IP Address

If you do not have a static IP address, you can modify the `~/.rix/setup.bash` file to use your public IP address.

On Linux:
```bash
export RIX_DEFAULT_IP=$(hostname -I | xargs)
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