import threading

from rixcore.impl.sub_impl import SubImplBase


class Subscriber:
    def __init__(self, impl: SubImplBase):
        self.mutex = threading.Lock()
        self.impl = impl

    def getTopic(self) -> str:
        if not self.ok():
            return ""
        self.mutex.acquire()
        topic = self.impl.get_info().topic_info.name
        self.mutex.release()
        return topic

    def getNumPublishers(self) -> int:
        if not self.ok():
            return 0
        self.mutex.acquire()
        num_pubs = self.impl.getNumPublishers()
        self.mutex.release()
        return num_pubs
    
    def ok(self) -> bool:
        self.mutex.acquire()
        if self.impl is None:
            status = False
        else:
            status = self.impl.ok()
        self.mutex.release()
        return status

    def _shutdown(self):
        if not self.ok():
            return
        self.mutex.acquire()
        self.impl.shutdown()
        self.mutex.release()

    def _addPublishers(self, pubs: list) -> None:
        self.mutex.acquire()
        self.impl.addPublishers(pubs)
        self.mutex.release()

    def _removePublishers(self, pubs: list) -> None:
        self.mutex.acquire()
        self.impl.removePublishers(pubs)
        self.mutex.release()
