import unittest
from unittest.mock import Mock, patch, MagicMock, call
import threading
import time
from rix.rix.core.publisher import Publisher
from rix.rix.core.subscriber import Subscriber
from rix.rix.core.service import Service
from rix.rix.core.service_client import ServiceClient
from rix.rix.core.socket import Socket
from rix.rix.core.common import OPCODE, DEFAULT_IP
from rix.msg.message import Message
from rix.msg.mediator.PubInfo import PubInfo
from rix.msg.mediator.SubInfo import SubInfo
from rix.msg.mediator.SrvInfo import SrvInfo
from rix.msg.mediator.SrvRequest import SrvRequest
from rix.msg.mediator.SrvResponse import SrvResponse
from rix.msg.mediator.SubNotify import SubNotify
from rix.msg.mediator.Operation import Operation
from rix.msg.mediator.Status import Status
from rix.msg.geometry.Point import Point


class MockMessage(Message):
    """Mock message class for testing"""
    def __init__(self, hash_value=12345, data="test_data"):
        self._hash_value = hash_value
        self.data = data
    
    def hash(self):
        return [self._hash_value]
    
    def size(self):
        return 100
    
    def serialize(self, buffer):
        buffer.extend(self.data.encode())
    
    def deserialize(self, buffer, offset):
        self.data = buffer[offset.offset:].decode()


class TestPublisherSubscriber(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_socket_patcher = patch('rix.rix.core.publisher.Socket')
        self.mock_socket_class = self.mock_socket_patcher.start()
        self.mock_socket_instance = Mock()
        self.mock_socket_class.return_value = self.mock_socket_instance
        
        # Mock successful socket operations by default
        self.mock_socket_instance.set_reuse_address.return_value = True
        self.mock_socket_instance.bind.return_value = True
        self.mock_socket_instance.listen.return_value = True
        self.mock_socket_instance.local_endpoint.return_value = ("127.0.0.1", 8080)
        self.mock_socket_instance.connect.return_value = True
        self.mock_socket_instance.send_message.return_value = True
        self.mock_socket_instance.recv_message_with_opcode.return_value = True
        
        # Mock successful registration response
        def mock_recv_success(op, status):
            op.opcode = OPCODE.STATUS_RESPONSE
            status.error = 0
            return True
        
        self.mock_socket_instance.recv_message_with_opcode.side_effect = mock_recv_success

    def tearDown(self):
        """Clean up after each test method."""
        self.mock_socket_patcher.stop()

    def create_pub_info(self, topic="/test_topic", node_id=123):
        """Helper to create PubInfo"""
        info = PubInfo()
        info.id = 456
        info.node_id = node_id
        info.topic_info.name = topic
        info.topic_info.message_hash = [12345]
        info.endpoint.address = DEFAULT_IP
        info.endpoint.port = 0
        return info

    def create_sub_info(self, topic="/test_topic", node_id=123):
        """Helper to create SubInfo"""
        info = SubInfo()
        info.id = 789
        info.node_id = node_id
        info.topic_info.name = topic
        info.topic_info.message_hash = [12345]
        info.endpoint.address = DEFAULT_IP
        info.endpoint.port = 0
        return info

    def test_publisher_initialization_success(self):
        """Test successful publisher initialization"""
        info = self.create_pub_info()
        publisher = Publisher(info)
        
        self.assertTrue(publisher.ok())
        self.assertTrue(publisher.registered_flag)
        self.assertFalse(publisher.shutdown_flag)
        
        # Verify socket setup calls
        self.mock_socket_instance.set_reuse_address.assert_called_once_with(True)
        self.mock_socket_instance.bind.assert_called_once()
        self.mock_socket_instance.listen.assert_called_once_with(32)
        self.mock_socket_instance.connect.assert_called_once()
        self.mock_socket_instance.send_message.assert_called_once_with(OPCODE.PUB_REGISTER, info)

    def test_publisher_initialization_bind_failure(self):
        """Test publisher initialization with bind failure"""
        self.mock_socket_instance.bind.return_value = False
        
        info = self.create_pub_info()
        publisher = Publisher(info)
        
        self.assertFalse(publisher.ok())
        self.assertFalse(publisher.registered_flag)
        self.assertTrue(publisher.shutdown_flag)

    def test_publisher_initialization_registration_failure(self):
        """Test publisher initialization with registration failure"""
        def mock_recv_error(op, status):
            op.opcode = OPCODE.STATUS_RESPONSE
            status.error = 1  # Error
            return True
        
        self.mock_socket_instance.recv_message_with_opcode.side_effect = mock_recv_error
        
        info = self.create_pub_info()
        publisher = Publisher(info)
        
        self.assertFalse(publisher.ok())
        self.assertFalse(publisher.registered_flag)

    def test_publisher_publish_success(self):
        """Test successful message publishing"""
        info = self.create_pub_info()
        publisher = Publisher(info)
        
        # Add mock connections
        mock_conn1 = Mock()
        mock_conn1.send_message.return_value = True
        mock_conn2 = Mock()
        mock_conn2.send_message.return_value = True
        
        publisher.connections.add(mock_conn1)
        publisher.connections.add(mock_conn2)
        
        msg = MockMessage(12345, "test message")
        publisher.publish(msg)
        
        # Verify message was sent to all connections
        mock_conn1.send_message.assert_called_once_with(OPCODE.PUB_MESSAGE, msg)
        mock_conn2.send_message.assert_called_once_with(OPCODE.PUB_MESSAGE, msg)

    def test_publisher_publish_message_type_mismatch(self):
        """Test publishing with wrong message type"""
        info = self.create_pub_info()
        publisher = Publisher(info)
        
        msg = MockMessage(99999, "wrong type")  # Different hash
        
        with patch('builtins.print') as mock_print:
            publisher.publish(msg)
            mock_print.assert_called_once_with("Warning: Message type mismatch in publish!")

    def test_publisher_publish_connection_failure(self):
        """Test publishing with connection failure"""
        info = self.create_pub_info()
        publisher = Publisher(info)
        
        # Add mock connections - one fails, one succeeds
        mock_conn_fail = Mock()
        mock_conn_fail.send_message.return_value = False
        mock_conn_success = Mock()
        mock_conn_success.send_message.return_value = True
        
        publisher.connections.add(mock_conn_fail)
        publisher.connections.add(mock_conn_success)
        
        msg = MockMessage(12345, "test message")
        publisher.publish(msg)
        
        # Failed connection should be removed
        self.assertNotIn(mock_conn_fail, publisher.connections)
        self.assertIn(mock_conn_success, publisher.connections)

    def test_publisher_spin_once_new_connection(self):
        """Test publisher accepting new connections"""
        info = self.create_pub_info()
        publisher = Publisher(info)
        
        # Mock server accepting new connection
        self.mock_socket_instance.is_readable.return_value = True
        mock_new_conn = Mock()
        self.mock_socket_instance.accept.return_value = (mock_new_conn, ("127.0.0.1", 9090))
        
        initial_connections = len(publisher.connections)
        publisher.spin_once()
        
        # New connection should be added
        self.assertEqual(len(publisher.connections), initial_connections + 1)
        self.assertIn(mock_new_conn, publisher.connections)

    def test_publisher_destructor(self):
        """Test publisher destructor"""
        info = self.create_pub_info()
        publisher = Publisher(info)
        
        # Reset mock to clear initialization calls
        self.mock_socket_class.reset_mock()
        self.mock_socket_instance.reset_mock()
        
        publisher.__del__()
        
        # Verify deregistration
        self.mock_socket_class.assert_called_once()
        self.mock_socket_instance.connect.assert_called_once()
        self.mock_socket_instance.send_message.assert_called_once_with(OPCODE.PUB_DEREGISTER, info)

    @patch('rix.rix.core.subscriber.Socket')
    def test_subscriber_initialization_success(self, mock_sub_socket_class):
        """Test successful subscriber initialization"""
        mock_sub_socket_instance = Mock()
        mock_sub_socket_class.return_value = mock_sub_socket_instance
        
        # Mock successful socket operations
        mock_sub_socket_instance.set_reuse_address.return_value = True
        mock_sub_socket_instance.bind.return_value = True
        mock_sub_socket_instance.listen.return_value = True
        mock_sub_socket_instance.local_endpoint.return_value = ("127.0.0.1", 8081)
        mock_sub_socket_instance.connect.return_value = True
        mock_sub_socket_instance.send_message.return_value = True
        
        def mock_recv_success(op, status):
            op.opcode = OPCODE.STATUS_RESPONSE
            status.error = 0
            return True
        
        mock_sub_socket_instance.recv_message_with_opcode.side_effect = mock_recv_success
        
        info = self.create_sub_info()
        subscriber = Subscriber(info, ("127.0.0.1", 8000))
        
        self.assertTrue(subscriber.ok())
        self.assertTrue(subscriber.registered_flag)
        self.assertFalse(subscriber.shutdown_flag)

    @patch('rix.rix.core.subscriber.Socket')
    def test_subscriber_set_callback(self, mock_sub_socket_class):
        """Test setting subscriber callback"""
        mock_sub_socket_instance = Mock()
        mock_sub_socket_class.return_value = mock_sub_socket_instance
        
        # Mock successful initialization
        mock_sub_socket_instance.set_reuse_address.return_value = True
        mock_sub_socket_instance.bind.return_value = True
        mock_sub_socket_instance.listen.return_value = True
        mock_sub_socket_instance.local_endpoint.return_value = ("127.0.0.1", 8081)
        mock_sub_socket_instance.connect.return_value = True
        mock_sub_socket_instance.send_message.return_value = True
        
        def mock_recv_success(op, status):
            op.opcode = OPCODE.STATUS_RESPONSE
            status.error = 0
            return True
        
        mock_sub_socket_instance.recv_message_with_opcode.side_effect = mock_recv_success
        
        info = self.create_sub_info()
        subscriber = Subscriber(info, ("127.0.0.1", 8000))
        
        callback = Mock()
        result = subscriber.set_callback(lambda: MockMessage(12345), callback)
        
        self.assertTrue(result)
        self.assertEqual(subscriber.callback, callback)
        self.assertIsNotNone(subscriber.message_instance)

    @patch('rix.rix.core.subscriber.Socket')
    def test_subscriber_set_callback_type_mismatch(self, mock_sub_socket_class):
        """Test setting callback with wrong message type"""
        mock_sub_socket_instance = Mock()
        mock_sub_socket_class.return_value = mock_sub_socket_instance
        
        # Mock successful initialization
        mock_sub_socket_instance.set_reuse_address.return_value = True
        mock_sub_socket_instance.bind.return_value = True
        mock_sub_socket_instance.listen.return_value = True
        mock_sub_socket_instance.local_endpoint.return_value = ("127.0.0.1", 8081)
        mock_sub_socket_instance.connect.return_value = True
        mock_sub_socket_instance.send_message.return_value = True
        
        def mock_recv_success(op, status):
            op.opcode = OPCODE.STATUS_RESPONSE
            status.error = 0
            return True
        
        mock_sub_socket_instance.recv_message_with_opcode.side_effect = mock_recv_success
        
        info = self.create_sub_info()
        subscriber = Subscriber(info, ("127.0.0.1", 8000))
        
        callback = Mock()
        result = subscriber.set_callback(lambda: MockMessage(99999), callback)  # Wrong hash
        
        self.assertFalse(result)

    @patch('rix.rix.core.subscriber.Socket')
    def test_subscriber_spin_once_publisher_notification(self, mock_sub_socket_class):
        """Test subscriber receiving publisher notifications"""
        mock_sub_socket_instance = Mock()
        mock_sub_socket_class.return_value = mock_sub_socket_instance
        
        # Mock successful initialization
        mock_sub_socket_instance.set_reuse_address.return_value = True
        mock_sub_socket_instance.bind.return_value = True
        mock_sub_socket_instance.listen.return_value = True
        mock_sub_socket_instance.local_endpoint.return_value = ("127.0.0.1", 8081)
        mock_sub_socket_instance.connect.return_value = True
        mock_sub_socket_instance.send_message.return_value = True
        
        def mock_recv_success(op, status):
            op.opcode = OPCODE.STATUS_RESPONSE
            status.error = 0
            return True
        
        mock_sub_socket_instance.recv_message_with_opcode.side_effect = mock_recv_success
        
        info = self.create_sub_info()
        subscriber = Subscriber(info, ("127.0.0.1", 8000))
        
        # Mock server accepting connection and receiving SubNotify
        mock_sub_socket_instance.is_readable.return_value = True
        mock_conn = Mock()
        mock_sub_socket_instance.accept.return_value = (mock_conn, ("127.0.0.1", 9090))
        
        def mock_recv_sub_notify(op, sub_notify):
            op.opcode = OPCODE.SUB_NOTIFY
            # Mock publisher info
            pub_info = PubInfo()
            pub_info.endpoint.address = "127.0.0.1"
            pub_info.endpoint.port = 8080
            sub_notify.publishers = [pub_info]
            return True
        
        mock_conn.recv_message_with_opcode.side_effect = mock_recv_sub_notify
        
        # Mock client socket for connecting to publisher
        mock_client_socket = Mock()
        mock_sub_socket_class.return_value = mock_client_socket
        mock_client_socket.set_blocking.return_value = True
        mock_client_socket.connect.return_value = True
        
        initial_clients = len(subscriber.clients)
        subscriber.spin_once()
        
        # Should have connected to the publisher
        self.assertEqual(len(subscriber.clients), initial_clients + 1)


class TestServiceCommunication(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_socket_patcher = patch('rix.rix.core.service.Socket')
        self.mock_socket_class = self.mock_socket_patcher.start()
        self.mock_socket_instance = Mock()
        self.mock_socket_class.return_value = self.mock_socket_instance
        
        # Mock successful socket operations by default
        self.mock_socket_instance.set_reuse_address.return_value = True
        self.mock_socket_instance.bind.return_value = True
        self.mock_socket_instance.listen.return_value = True
        self.mock_socket_instance.local_endpoint.return_value = ("127.0.0.1", 8082)
        self.mock_socket_instance.connect.return_value = True
        self.mock_socket_instance.send_message.return_value = True
        
        # Mock successful registration response
        def mock_recv_success(op, status):
            op.opcode = OPCODE.STATUS_RESPONSE
            status.error = 0
            return True
        
        self.mock_socket_instance.recv_message_with_opcode.side_effect = mock_recv_success

    def tearDown(self):
        """Clean up after each test method."""
        self.mock_socket_patcher.stop()

    def create_srv_info(self, service_name="/test_service", node_id=123):
        """Helper to create SrvInfo"""
        info = SrvInfo()
        info.id = 456
        info.node_id = node_id
        info.name = service_name
        info.request_hash = [11111]
        info.response_hash = [22222]
        info.endpoint.address = DEFAULT_IP
        info.endpoint.port = 0
        return info

    def create_srv_request(self, service_name="/test_service", node_id=123):
        """Helper to create SrvRequest"""
        request = SrvRequest()
        request.name = service_name
        request.node_id = node_id
        request.request_hash = [11111]
        request.response_hash = [22222]
        return request

    def test_service_initialization_success(self):
        """Test successful service initialization"""
        info = self.create_srv_info()
        service = Service(info)
        
        self.assertTrue(service.ok())
        self.assertTrue(service.registered_flag)
        self.assertFalse(service.shutdown_flag)
        
        # Verify socket setup calls
        self.mock_socket_instance.set_reuse_address.assert_called_once_with(True)
        self.mock_socket_instance.bind.assert_called_once()
        self.mock_socket_instance.listen.assert_called_once_with(32)
        self.mock_socket_instance.connect.assert_called_once()
        self.mock_socket_instance.send_message.assert_called_once_with(OPCODE.SRV_REGISTER, info)

    def test_service_initialization_bind_failure(self):
        """Test service initialization with bind failure"""
        self.mock_socket_instance.bind.return_value = False
        
        info = self.create_srv_info()
        service = Service(info)
        
        self.assertFalse(service.ok())
        self.assertFalse(service.registered_flag)
        self.assertTrue(service.shutdown_flag)

    def test_service_set_callback_success(self):
        """Test setting service callback"""
        info = self.create_srv_info()
        service = Service(info)
        
        request_type = lambda: MockMessage(11111)
        response_type = lambda: MockMessage(22222)
        callback = Mock()
        
        result = service.set_callback(request_type, response_type, callback)
        
        self.assertTrue(result)
        self.assertEqual(service.callback, callback)
        self.assertIsNotNone(service.request_instance)
        self.assertIsNotNone(service.response_instance)

    def test_service_set_callback_type_mismatch(self):
        """Test setting callback with wrong message types"""
        info = self.create_srv_info()
        service = Service(info)
        
        request_type = lambda: MockMessage(99999)  # Wrong hash
        response_type = lambda: MockMessage(22222)
        callback = Mock()
        
        result = service.set_callback(request_type, response_type, callback)
        
        self.assertFalse(result)

    def test_service_spin_once_request_handling(self):
        """Test service handling incoming requests"""
        info = self.create_srv_info()
        service = Service(info)
        
        # Set up callback
        request_type = lambda: MockMessage(11111)
        response_type = lambda: MockMessage(22222)
        callback = Mock()
        service.set_callback(request_type, response_type, callback)
        
        # Mock server accepting connection
        self.mock_socket_instance.is_readable.return_value = True
        mock_conn = Mock()
        self.mock_socket_instance.accept.return_value = (mock_conn, ("127.0.0.1", 9091))
        
        # Mock receiving service request
        def mock_recv_request(op, request):
            op.opcode = OPCODE.SRV_REQUEST_MESSAGE
            request.data = "test_request"
            return True
        
        mock_conn.recv_message_with_opcode.side_effect = mock_recv_request
        mock_conn.send_message.return_value = True
        mock_conn.close.return_value = None
        
        service.spin_once()
        
        # Verify callback was called and response was sent
        callback.assert_called_once()
        mock_conn.send_message.assert_called_once_with(OPCODE.SRV_RESPONSE_MESSAGE, service.response_instance)
        mock_conn.close.assert_called_once()

    def test_service_spin_once_no_callback(self):
        """Test service spin_once when no callback is set"""
        info = self.create_srv_info()
        service = Service(info)
        
        # Mock server accepting connection
        self.mock_socket_instance.is_readable.return_value = True
        mock_conn = Mock()
        self.mock_socket_instance.accept.return_value = (mock_conn, ("127.0.0.1", 9091))
        
        service.spin_once()
        
        # Should not attempt to receive messages without callback
        mock_conn.recv_message_with_opcode.assert_not_called()

    def test_service_destructor(self):
        """Test service destructor"""
        info = self.create_srv_info()
        service = Service(info)
        
        # Reset mock to clear initialization calls
        self.mock_socket_class.reset_mock()
        self.mock_socket_instance.reset_mock()
        
        service.__del__()
        
        # Verify deregistration and server close
        self.mock_socket_class.assert_called_once()
        self.mock_socket_instance.connect.assert_called_once()
        self.mock_socket_instance.send_message.assert_called_once_with(OPCODE.SRV_DEREGISTER, info)
        self.mock_socket_instance.close.assert_called_once()

    @patch('rix.rix.core.service_client.Socket')
    def test_service_client_initialization_success(self, mock_client_socket_class):
        """Test successful service client initialization"""
        mock_client_socket_instance = Mock()
        mock_client_socket_class.return_value = mock_client_socket_instance
        
        # Mock successful connection and service discovery
        mock_client_socket_instance.connect.return_value = True
        mock_client_socket_instance.send_message.return_value = True
        
        def mock_recv_service_response(op, response):
            op.opcode = OPCODE.SRV_RESPONSE
            response.error = 0
            response.srv_info.endpoint.address = "127.0.0.1"
            response.srv_info.endpoint.port = 8082
            return True
        
        mock_client_socket_instance.recv_message_with_opcode.side_effect = mock_recv_service_response
        
        request = self.create_srv_request()
        client = ServiceClient(request)
        
        self.assertTrue(client.ok())
        self.assertFalse(client.shutdown_flag)
        self.assertEqual(client.endpoint, ("127.0.0.1", 8082))

    @patch('rix.rix.core.service_client.Socket')
    def test_service_client_initialization_service_not_found(self, mock_client_socket_class):
        """Test service client initialization when service is not found"""
        mock_client_socket_instance = Mock()
        mock_client_socket_class.return_value = mock_client_socket_instance
        
        # Mock connection success but service error
        mock_client_socket_instance.connect.return_value = True
        mock_client_socket_instance.send_message.return_value = True
        
        def mock_recv_service_error(op, response):
            op.opcode = OPCODE.SRV_RESPONSE
            response.error = 1  # Service not found
            return True
        
        mock_client_socket_instance.recv_message_with_opcode.side_effect = mock_recv_service_error
        
        request = self.create_srv_request()
        client = ServiceClient(request)
        
        self.assertFalse(client.ok())
        self.assertTrue(client.shutdown_flag)

    @patch('rix.rix.core.service_client.Socket')
    def test_service_client_call_success(self, mock_client_socket_class):
        """Test successful service client call"""
        mock_client_socket_instance = Mock()
        mock_client_socket_class.return_value = mock_client_socket_instance
        
        # Mock successful initialization
        mock_client_socket_instance.connect.return_value = True
        mock_client_socket_instance.send_message.return_value = True
        
        def mock_recv_service_response(op, response):
            op.opcode = OPCODE.SRV_RESPONSE
            response.error = 0
            response.srv_info.endpoint.address = "127.0.0.1"
            response.srv_info.endpoint.port = 8082
            return True
        
        mock_client_socket_instance.recv_message_with_opcode.side_effect = mock_recv_service_response
        
        request = self.create_srv_request()
        client = ServiceClient(request)
        
        # Reset mock for the actual call
        mock_client_socket_class.reset_mock()
        mock_call_socket = Mock()
        mock_client_socket_class.return_value = mock_call_socket
        mock_call_socket.connect.return_value = True
        mock_call_socket.send_message.return_value = True
        
        def mock_recv_call_response(op, response):
            op.opcode = OPCODE.SRV_RESPONSE_MESSAGE
            response.data = "response_data"
            return True
        
        mock_call_socket.recv_message_with_opcode.side_effect = mock_recv_call_response
        
        request_msg = MockMessage(11111, "request_data")
        response_msg = MockMessage(22222)
        
        result = client.call(request_msg, response_msg)
        
        self.assertTrue(result)
        mock_call_socket.connect.assert_called_once_with(("127.0.0.1", 8082))
        mock_call_socket.send_message.assert_called_once_with(OPCODE.SRV_REQUEST_MESSAGE, request_msg)

    @patch('rix.rix.core.service_client.Socket')
    def test_service_client_call_connection_failure(self, mock_client_socket_class):
        """Test service client call with connection failure"""
        mock_client_socket_instance = Mock()
        mock_client_socket_class.return_value = mock_client_socket_instance
        
        # Mock successful initialization
        mock_client_socket_instance.connect.return_value = True
        mock_client_socket_instance.send_message.return_value = True
        
        def mock_recv_service_response(op, response):
            op.opcode = OPCODE.SRV_RESPONSE
            response.error = 0
            response.srv_info.endpoint.address = "127.0.0.1"
            response.srv_info.endpoint.port = 8082
            return True
        
        mock_client_socket_instance.recv_message_with_opcode.side_effect = mock_recv_service_response
        
        request = self.create_srv_request()
        client = ServiceClient(request)
        
        # Reset mock for the actual call - connection fails
        mock_client_socket_class.reset_mock()
        mock_call_socket = Mock()
        mock_client_socket_class.return_value = mock_call_socket
        mock_call_socket.connect.return_value = False  # Connection failure
        
        request_msg = MockMessage(11111, "request_data")
        response_msg = MockMessage(22222)
        
        result = client.call(request_msg, response_msg)
        
        self.assertFalse(result)


class TestIntegratedCommunication(unittest.TestCase):
    """Integration tests for publisher-subscriber and service-client communication"""
    
    def setUp(self):
        """Set up test fixtures for integration tests."""
        # We'll use more realistic mocking for integration tests
        pass

    @patch('rix.rix.core.publisher.Socket')
    @patch('rix.rix.core.subscriber.Socket')
    def test_publisher_subscriber_integration(self, mock_sub_socket, mock_pub_socket):
        """Test integrated publisher-subscriber communication"""
        # Set up publisher mock
        pub_socket_instance = Mock()
        mock_pub_socket.return_value = pub_socket_instance
        pub_socket_instance.set_reuse_address.return_value = True
        pub_socket_instance.bind.return_value = True
        pub_socket_instance.listen.return_value = True
        pub_socket_instance.local_endpoint.return_value = ("127.0.0.1", 8080)
        pub_socket_instance.connect.return_value = True
        pub_socket_instance.send_message.return_value = True
        
        def pub_recv_success(op, status):
            op.opcode = OPCODE.STATUS_RESPONSE
            status.error = 0
            return True
        
        pub_socket_instance.recv_message_with_opcode.side_effect = pub_recv_success
        
        # Set up subscriber mock
        sub_socket_instance = Mock()
        mock_sub_socket.return_value = sub_socket_instance
        sub_socket_instance.set_reuse_address.return_value = True
        sub_socket_instance.bind.return_value = True
        sub_socket_instance.listen.return_value = True
        sub_socket_instance.local_endpoint.return_value = ("127.0.0.1", 8081)
        sub_socket_instance.connect.return_value = True
        sub_socket_instance.send_message.return_value = True
        
        def sub_recv_success(op, status):
            op.opcode = OPCODE.STATUS_RESPONSE
            status.error = 0
            return True
        
        sub_socket_instance.recv_message_with_opcode.side_effect = sub_recv_success
        
        # Create publisher and subscriber
        pub_info = PubInfo()
        pub_info.id = 456
        pub_info.topic_info.name = "/test_topic"
        pub_info.topic_info.message_hash = [12345]
        pub_info.endpoint.address = "127.0.0.1"
        pub_info.endpoint.port = 0
        
        sub_info = SubInfo()
        sub_info.id = 789
        sub_info.topic_info.name = "/test_topic"
        sub_info.topic_info.message_hash = [12345]
        sub_info.endpoint.address = "127.0.0.1"
        sub_info.endpoint.port = 0
        
        publisher = Publisher(pub_info)
        subscriber = Subscriber(sub_info, ("127.0.0.1", 8000))
        
        # Verify both initialized successfully
        self.assertTrue(publisher.ok())
        self.assertTrue(subscriber.ok())
        
        # Test message publishing (simplified)
        mock_connection = Mock()
        mock_connection.send_message.return_value = True
        publisher.connections.add(mock_connection)
        
        test_message = MockMessage(12345, "Hello, Subscriber!")
        publisher.publish(test_message)
        
        mock_connection.send_message.assert_called_once_with(OPCODE.PUB_MESSAGE, test_message)

    @patch('rix.rix.core.service.Socket')
    @patch('rix.rix.core.service_client.Socket')
    def test_service_client_integration(self, mock_client_socket, mock_service_socket):
        """Test integrated service-client communication"""
        # Set up service mock
        service_socket_instance = Mock()
        mock_service_socket.return_value = service_socket_instance
        service_socket_instance.set_reuse_address.return_value = True
        service_socket_instance.bind.return_value = True
        service_socket_instance.listen.return_value = True
        service_socket_instance.local_endpoint.return_value = ("127.0.0.1", 8082)
        service_socket_instance.connect.return_value = True
        service_socket_instance.send_message.return_value = True
        
        def service_recv_success(op, status):
            op.opcode = OPCODE.STATUS_RESPONSE
            status.error = 0
            return True
        
        service_socket_instance.recv_message_with_opcode.side_effect = service_recv_success
        
        # Set up client mock
        client_socket_instance = Mock()
        mock_client_socket.return_value = client_socket_instance
        client_socket_instance.connect.return_value = True
        client_socket_instance.send_message.return_value = True
        
        def client_recv_success(op, response):
            op.opcode = OPCODE.SRV_RESPONSE
            response.error = 0
            response.srv_info.endpoint.address = "127.0.0.1"
            response.srv_info.endpoint.port = 8082
            return True
        
        client_socket_instance.recv_message_with_opcode.side_effect = client_recv_success
        
        # Create service and client
        srv_info = SrvInfo()
        srv_info.id = 456
        srv_info.name = "/test_service"
        srv_info.request_hash = [11111]
        srv_info.response_hash = [22222]
        srv_info.endpoint.address = "127.0.0.1"
        srv_info.endpoint.port = 0
        
        srv_request = SrvRequest()
        srv_request.name = "/test_service"
        srv_request.node_id = 123
        srv_request.request_hash = [11111]
        srv_request.response_hash = [22222]
        
        service = Service(srv_info)
        client = ServiceClient(srv_request)
        
        # Verify both initialized successfully
        self.assertTrue(service.ok())
        self.assertTrue(client.ok())
        
        # Set up service callback
        def test_callback(req, res):
            res.data = f"Response to: {req.data}"
        
        service.set_callback(
            lambda: MockMessage(11111), 
            lambda: MockMessage(22222), 
            test_callback
        )
        
        self.assertIsNotNone(service.callback)


if __name__ == '__main__':
    unittest.main()