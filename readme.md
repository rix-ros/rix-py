# RIX-PY

RIX-PY is a Python implementation of the `rix-core` library.

## Tests
Set up a virtual environment to run the tests in.
```bash
cd test
python3 -m venv venv
source venv/bin/activate
pip install ~/.rix/python/rixmsg
pip install ../rix-py/rixcore
```

Run the `rixhub` executable
```bash
rixhub
```

Simple tests
```bash
python3 [rix_simple_pub | rix_simple_sub].py
```

Video publisher, optionally specify `cv2.VideoCapture` index
```bash
python3 video_pub.py [--camera N]
```

Video subscriber, optionally use compressed message type
```bash
python3 video_sub.py [--use-jpg]
```