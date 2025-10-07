import unittest
from unittest.mock import Mock, patch, MagicMock, call
import random
from rix.core.node import Node
from rix.core.socket import Socket
from rix.core.common import OPCODE, RIXHUB_IP, RIXHUB_PORT, DEFAULT_IP
from rix.core.spinner import Spinner
from rix.core.publisher import Publisher
from rix.core.subscriber import Subscriber
from rix.core.service import Service
from rix.core.service_client import ServiceClient
from rix.core.timer import Timer
from rix.msg.message import Message
from rix.msg.mediator.NodeInfo import NodeInfo
from rix.msg.mediator.PubInfo import PubInfo
from rix.msg.mediator.SubInfo import SubInfo
from rix.msg.mediator.SrvInfo import SrvInfo
from rix.msg.mediator.SrvRequest import SrvRequest
from rix.msg.mediator.ParamInfo import ParamInfo
from rix.msg.mediator.SystemInfo import SystemInfo
from rix.msg.mediator.Operation import Operation
from rix.msg.mediator.Status import Status
from rix.msg.standard.UInt64 import UInt64


class MockMessage(Message):
    """Mock message class for testing"""
    def __init__(self, hash_value=12345):
        self._hash_value = hash_value
    
    def hash(self):
        return [self._hash_value]
    
    def size(self):
        return 100
    
    def serialize(self, buffer):
        buffer.extend(b'mock_data')
    
    def deserialize(self, buffer, offset):
        pass


class TestNode(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_socket_patcher = patch('rix.core.node.Socket')
        self.mock_socket_class = self.mock_socket_patcher.start()
        self.mock_socket_instance = Mock()
        self.mock_socket_class.return_value = self.mock_socket_instance
        
        # Mock successful connection and registration by default
        self.mock_socket_instance.connect.return_value = True
        self.mock_socket_instance.send_message.return_value = True
        self.mock_socket_instance.recv_message_with_opcode.return_value = True
        
        # Mock successful status response
        def mock_recv_message_with_opcode(op, status):
            op.opcode = OPCODE.STATUS_RESPONSE
            status.error = 0
            return True
        
        self.mock_socket_instance.recv_message_with_opcode.side_effect = mock_recv_message_with_opcode

    def tearDown(self):
        """Clean up after each test method."""
        self.mock_socket_patcher.stop()

    @patch('rix.core.node.Node._Node__generateID')
    @patch('rix.core.node.Node._Node__getMachineID')
    def test_node_initialization_success(self, mock_machine_id, mock_generate_id):
        """Test successful node initialization"""
        mock_generate_id.return_value = 123456
        mock_machine_id.return_value = 789
        
        node = Node("test_node")
        
        self.assertFalse(node.shutdown_flag)
        self.assertTrue(node.registered_flag)
        self.assertEqual(node.info.name, "test_node")
        self.assertEqual(node.info.id, 123456)
        self.assertEqual(node.info.machine_id, 789)
        self.assertEqual(node.rixhub_endpoint, (RIXHUB_IP, RIXHUB_PORT))
        
        # Verify socket interactions
        self.mock_socket_instance.connect.assert_called_once_with((RIXHUB_IP, RIXHUB_PORT))
        self.mock_socket_instance.send_message.assert_called_once_with(OPCODE.NODE_REGISTER, node.info)

    def test_node_initialization_connection_failure(self):
        """Test node initialization with connection failure"""
        self.mock_socket_instance.connect.return_value = False
        
        node = Node("test_node")
        
        self.assertTrue(node.shutdown_flag)
        self.assertFalse(node.registered_flag)

    def test_node_initialization_send_failure(self):
        """Test node initialization with send message failure"""
        self.mock_socket_instance.send_message.return_value = False
        
        node = Node("test_node")
        
        self.assertTrue(node.shutdown_flag)
        self.assertFalse(node.registered_flag)

    def test_node_initialization_recv_failure(self):
        """Test node initialization with receive message failure"""
        self.mock_socket_instance.recv_message_with_opcode.return_value = False
        self.mock_socket_instance.recv_message_with_opcode.side_effect = None  # Clear the side_effect
        
        node = Node("test_node")
        
        self.assertTrue(node.shutdown_flag)
        self.assertFalse(node.registered_flag)

    def test_node_initialization_invalid_opcode(self):
        """Test node initialization with invalid opcode response"""
        def mock_recv_invalid_opcode(op, status):
            op.opcode = OPCODE.PUB_MESSAGE  # Wrong opcode
            return True
        
        self.mock_socket_instance.recv_message_with_opcode.side_effect = mock_recv_invalid_opcode
        
        node = Node("test_node")
        
        self.assertTrue(node.shutdown_flag)
        self.assertFalse(node.registered_flag)

    def test_node_initialization_error_status(self):
        """Test node initialization with error status"""
        def mock_recv_error_status(op, status):
            op.opcode = OPCODE.STATUS_RESPONSE
            status.error = 1  # Error condition
            return True
        
        self.mock_socket_instance.recv_message_with_opcode.side_effect = mock_recv_error_status
        
        node = Node("test_node")
        
        self.assertTrue(node.shutdown_flag)
        self.assertFalse(node.registered_flag)

    def test_node_custom_endpoint(self):
        """Test node initialization with custom endpoint"""
        custom_endpoint = ("192.168.1.100", 8080)
        node = Node("test_node", custom_endpoint)
        
        self.assertEqual(node.rixhub_endpoint, custom_endpoint)
        self.mock_socket_instance.connect.assert_called_once_with(custom_endpoint)

    def test_node_destructor_registered(self):
        """Test node destructor when registered"""
        node = Node("test_node")
        self.assertTrue(node.registered_flag)
        
        # Reset mock to clear initialization calls
        self.mock_socket_class.reset_mock()
        self.mock_socket_instance.reset_mock()
        
        # Trigger destructor
        node.__del__()
        
        # Verify deregistration
        self.mock_socket_class.assert_called_once()
        self.mock_socket_instance.connect.assert_called_once_with(node.rixhub_endpoint)
        self.mock_socket_instance.send_message.assert_called_once_with(OPCODE.NODE_DEREGISTER, node.info)

    def test_node_destructor_not_registered(self):
        """Test node destructor when not registered"""
        self.mock_socket_instance.connect.return_value = False
        node = Node("test_node")
        self.assertFalse(node.registered_flag)
        
        # Reset mock to clear initialization calls
        self.mock_socket_class.reset_mock()
        
        # Trigger destructor
        node.__del__()
        
        # Verify no deregistration attempt
        self.mock_socket_class.assert_not_called()

    def test_ok_method(self):
        """Test ok() method"""
        node = Node("test_node")
        
        self.assertTrue(node.ok())
        
        node.shutdown()
        self.assertFalse(node.ok())

    def test_shutdown_method(self):
        """Test shutdown() method"""
        node = Node("test_node")
        
        self.assertFalse(node.shutdown_flag)
        node.shutdown()
        self.assertTrue(node.shutdown_flag)

    @patch('rix.core.node.Publisher')
    @patch('rix.core.node.Node._Node__generateID')
    def test_create_publisher(self, mock_generate_id, mock_publisher_class):
        """Test create_publisher method"""
        mock_generate_id.return_value = 999
        mock_publisher_instance = Mock()
        mock_publisher_class.return_value = mock_publisher_instance
        
        node = Node("test_node")
        mock_msg = MockMessage(12345)
        
        publisher = node.create_publisher(lambda: mock_msg, "/test_topic")
        
        self.assertEqual(publisher, mock_publisher_instance)
        self.assertIn(mock_publisher_instance, node.components)
        
        # Verify PubInfo was created correctly
        call_args = mock_publisher_class.call_args
        pub_info = call_args[0][0]
        self.assertEqual(pub_info.id, 999)
        self.assertEqual(pub_info.node_id, node.info.id)
        self.assertEqual(pub_info.topic_info.name, "/test_topic")
        self.assertEqual(pub_info.topic_info.message_hash, [12345])
        self.assertEqual(pub_info.endpoint.address, DEFAULT_IP)
        self.assertEqual(pub_info.endpoint.port, 0)

    @patch('rix.core.node.Publisher')
    def test_create_publisher_custom_endpoint(self, mock_publisher_class):
        """Test create_publisher with custom endpoint"""
        mock_publisher_instance = Mock()
        mock_publisher_class.return_value = mock_publisher_instance
        
        node = Node("test_node")
        mock_msg = MockMessage()
        custom_endpoint = ("192.168.1.10", 5000)
        
        node.create_publisher(lambda: mock_msg, "/test_topic", custom_endpoint)
        
        call_args = mock_publisher_class.call_args
        pub_info = call_args[0][0]
        self.assertEqual(pub_info.endpoint.address, "192.168.1.10")
        self.assertEqual(pub_info.endpoint.port, 5000)

    @patch('rix.core.node.Subscriber')
    @patch('rix.core.node.Node._Node__generateID')
    def test_create_subscriber(self, mock_generate_id, mock_subscriber_class):
        """Test create_subscriber method"""
        mock_generate_id.return_value = 888
        mock_subscriber_instance = Mock()
        mock_subscriber_class.return_value = mock_subscriber_instance
        
        node = Node("test_node")
        mock_msg = MockMessage(54321)
        callback = Mock()
        
        subscriber = node.create_subscriber(lambda: mock_msg, "/test_topic", callback)
        
        self.assertEqual(subscriber, mock_subscriber_instance)
        self.assertIn(mock_subscriber_instance, node.components)
        
        # Verify SubInfo was created correctly
        call_args = mock_subscriber_class.call_args
        sub_info = call_args[0][0]
        self.assertEqual(sub_info.id, 888)
        self.assertEqual(sub_info.node_id, node.info.id)
        self.assertEqual(sub_info.topic_info.name, "/test_topic")
        self.assertEqual(sub_info.topic_info.message_hash, [54321])
        
        # Verify callback was set
        mock_subscriber_instance.set_callback.assert_called_once()

    @patch('rix.core.node.Service')
    @patch('rix.core.node.Node._Node__generateID')
    def test_create_service(self, mock_generate_id, mock_service_class):
        """Test create_service method"""
        mock_generate_id.return_value = 777
        mock_service_instance = Mock()
        mock_service_class.return_value = mock_service_instance
        
        node = Node("test_node")
        mock_request = MockMessage(11111)
        mock_response = MockMessage(22222)
        callback = Mock()
        
        service = node.create_service(
            lambda: mock_request, lambda: mock_response, "/test_service", callback
        )
        
        self.assertEqual(service, mock_service_instance)
        self.assertIn(mock_service_instance, node.components)
        
        # Verify SrvInfo was created correctly
        call_args = mock_service_class.call_args
        srv_info = call_args[0][0]
        self.assertEqual(srv_info.id, 777)
        self.assertEqual(srv_info.node_id, node.info.id)
        self.assertEqual(srv_info.name, "/test_service")
        self.assertEqual(srv_info.request_hash, [11111])
        self.assertEqual(srv_info.response_hash, [22222])
        
        # Verify callback was set
        mock_service_instance.set_callback.assert_called_once()

    @patch('rix.core.node.ServiceClient')
    def test_create_service_client(self, mock_service_client_class):
        """Test create_service_client method"""
        mock_service_client_instance = Mock()
        mock_service_client_class.return_value = mock_service_client_instance
        
        node = Node("test_node")
        mock_request = MockMessage(33333)
        mock_response = MockMessage(44444)
        
        service_client = node.create_service_client(
            lambda: mock_request, lambda: mock_response, "/test_service"
        )
        
        self.assertEqual(service_client, mock_service_client_instance)
        
        # Verify SrvRequest was created correctly
        call_args = mock_service_client_class.call_args
        srv_request = call_args[0][0]
        self.assertEqual(srv_request.name, "/test_service")
        self.assertEqual(srv_request.node_id, node.info.id)
        self.assertEqual(srv_request.request_hash, [33333])
        self.assertEqual(srv_request.response_hash, [44444])

    @patch('rix.core.node.Timer')
    def test_create_timer(self, mock_timer_class):
        """Test create_timer method"""
        mock_timer_instance = Mock()
        mock_timer_class.return_value = mock_timer_instance
        
        node = Node("test_node")
        callback = Mock()
        duration = 1.5
        
        timer = node.create_timer(duration, callback)
        
        self.assertEqual(timer, mock_timer_instance)
        self.assertIn(mock_timer_instance, node.components)
        
        # Verify Timer was created with correct parameters
        mock_timer_class.assert_called_once_with(duration, callback)

    def test_set_parameter_success(self):
        """Test successful set_parameter"""
        node = Node("test_node")
        mock_param = MockMessage()
        
        # Reset mock to clear initialization calls
        self.mock_socket_class.reset_mock()
        self.mock_socket_instance.reset_mock()
        
        # Set up successful parameter setting
        self.mock_socket_instance.connect.return_value = True
        self.mock_socket_instance.send_message.return_value = True
        
        def mock_recv_param_response(op, status):
            op.opcode = OPCODE.STATUS_RESPONSE
            status.error = 0
            return True
        
        self.mock_socket_instance.recv_message_with_opcode.side_effect = mock_recv_param_response
        
        result = node.set_parameter("test_param", mock_param)
        
        self.assertTrue(result)
        self.mock_socket_instance.connect.assert_called_once_with(node.rixhub_endpoint)
        self.mock_socket_instance.send_message.assert_called_once()
        
        # Verify ParamInfo was created correctly
        call_args = self.mock_socket_instance.send_message.call_args
        opcode = call_args[0][0]
        param_info = call_args[0][1]
        self.assertEqual(opcode, OPCODE.PARAM_SET_REQUEST)
        self.assertEqual(param_info.id, node.info.id)
        self.assertEqual(param_info.name, "test_param")
        self.assertEqual(param_info.message_hash, mock_param.hash())

    def test_set_parameter_connection_failure(self):
        """Test set_parameter with connection failure"""
        node = Node("test_node")
        mock_param = MockMessage()
        
        # Reset mock and set connection failure
        self.mock_socket_class.reset_mock()
        self.mock_socket_instance.reset_mock()
        self.mock_socket_instance.connect.return_value = False
        
        result = node.set_parameter("test_param", mock_param)
        
        self.assertFalse(result)

    def test_set_parameter_send_failure(self):
        """Test set_parameter with send failure"""
        node = Node("test_node")
        mock_param = MockMessage()
        
        # Reset mock and set send failure
        self.mock_socket_class.reset_mock()
        self.mock_socket_instance.reset_mock()
        self.mock_socket_instance.connect.return_value = True
        self.mock_socket_instance.send_message.return_value = False
        
        result = node.set_parameter("test_param", mock_param)
        
        self.assertFalse(result)

    def test_get_parameter_success(self):
        """Test successful get_parameter"""
        node = Node("test_node")
        mock_param = MockMessage()
        
        # Reset mock to clear initialization calls
        self.mock_socket_class.reset_mock()
        self.mock_socket_instance.reset_mock()
        
        # Set up successful parameter getting
        self.mock_socket_instance.connect.return_value = True
        self.mock_socket_instance.send_message.return_value = True
        
        def mock_recv_param_get_response(op, param_info):
            op.opcode = OPCODE.PARAM_GET_RESPONSE
            param_info.data = bytearray(b'param_data')
            return True
        
        self.mock_socket_instance.recv_message_with_opcode.side_effect = mock_recv_param_get_response
        
        result = node.get_parameter("test_param", mock_param)
        
        self.assertTrue(result)
        self.mock_socket_instance.connect.assert_called_once_with(node.rixhub_endpoint)
        
        # Verify two calls: send request and receive response
        self.assertEqual(self.mock_socket_instance.send_message.call_count, 1)
        self.assertEqual(self.mock_socket_instance.recv_message_with_opcode.call_count, 1)

    def test_get_parameter_invalid_opcode(self):
        """Test get_parameter with invalid opcode response"""
        node = Node("test_node")
        mock_param = MockMessage()
        
        # Reset mock
        self.mock_socket_class.reset_mock()
        self.mock_socket_instance.reset_mock()
        self.mock_socket_instance.connect.return_value = True
        self.mock_socket_instance.send_message.return_value = True
        
        def mock_recv_invalid_opcode(op, param_info):
            op.opcode = OPCODE.STATUS_RESPONSE  # Wrong opcode
            return True
        
        self.mock_socket_instance.recv_message_with_opcode.side_effect = mock_recv_invalid_opcode
        
        result = node.get_parameter("test_param", mock_param)
        
        self.assertFalse(result)

    def test_get_system_info_success(self):
        """Test successful get_system_info"""
        node = Node("test_node")
        system_info = SystemInfo()
        
        # Reset mock to clear initialization calls
        self.mock_socket_class.reset_mock()
        self.mock_socket_instance.reset_mock()
        
        # Set up successful system info getting
        self.mock_socket_instance.connect.return_value = True
        self.mock_socket_instance.send_message.return_value = True
        
        def mock_recv_system_info_response(op, info):
            op.opcode = OPCODE.SYSTEM_GET_RESPONSE
            return True
        
        self.mock_socket_instance.recv_message_with_opcode.side_effect = mock_recv_system_info_response
        
        result = node.get_system_info(system_info)
        
        self.assertTrue(result)
        self.mock_socket_instance.connect.assert_called_once_with(node.rixhub_endpoint)
        
        # Verify UInt64 message with node ID was sent
        call_args = self.mock_socket_instance.send_message.call_args
        opcode = call_args[0][0]
        node_id_msg = call_args[0][1]
        self.assertEqual(opcode, OPCODE.SYSTEM_GET_REQUEST)
        self.assertEqual(node_id_msg.data, node.info.id)

    def test_get_system_info_connection_failure(self):
        """Test get_system_info with connection failure"""
        node = Node("test_node")
        system_info = SystemInfo()
        
        # Reset mock and set connection failure
        self.mock_socket_class.reset_mock()
        self.mock_socket_instance.reset_mock()
        self.mock_socket_instance.connect.return_value = False
        
        result = node.get_system_info(system_info)
        
        self.assertFalse(result)

    def test_spin_once_healthy_components(self):
        """Test spin_once with healthy components"""
        node = Node("test_node")
        
        # Create mock components
        mock_component1 = Mock(spec=Spinner)
        mock_component1.ok.return_value = True
        mock_component2 = Mock(spec=Spinner)
        mock_component2.ok.return_value = True
        
        node.components.add(mock_component1)
        node.components.add(mock_component2)
        
        node.spin_once()
        
        # Verify all components were checked and spun
        mock_component1.ok.assert_called_once()
        mock_component1.spin_once.assert_called_once()
        mock_component2.ok.assert_called_once()
        mock_component2.spin_once.assert_called_once()
        
        # Verify components are still in the set
        self.assertIn(mock_component1, node.components)
        self.assertIn(mock_component2, node.components)

    def test_spin_once_unhealthy_components(self):
        """Test spin_once with unhealthy components"""
        node = Node("test_node")
        
        # Create mock components - one healthy, one unhealthy
        mock_healthy = Mock(spec=Spinner)
        mock_healthy.ok.return_value = True
        mock_unhealthy = Mock(spec=Spinner)
        mock_unhealthy.ok.return_value = False
        
        node.components.add(mock_healthy)
        node.components.add(mock_unhealthy)
        
        node.spin_once()
        
        # Verify healthy component was spun
        mock_healthy.ok.assert_called_once()
        mock_healthy.spin_once.assert_called_once()
        
        # Verify unhealthy component was checked but not spun
        mock_unhealthy.ok.assert_called_once()
        mock_unhealthy.spin_once.assert_not_called()
        
        # Verify unhealthy component was removed
        self.assertIn(mock_healthy, node.components)
        self.assertNotIn(mock_unhealthy, node.components)

    def test_spin_once_empty_components(self):
        """Test spin_once with no components"""
        node = Node("test_node")
        
        # Should not raise any exceptions
        node.spin_once()
        
        self.assertEqual(len(node.components), 0)

    @patch('rix.core.node.random.getrandbits')
    def test_generate_id_through_node_creation(self, mock_getrandbits):
        """Test __generateID static method through node creation"""
        mock_getrandbits.return_value = 987654321
        
        node = Node("test_node")
        
        # The node ID should be generated using the mocked random function
        self.assertEqual(node.info.id, 987654321)
        # getrandbits should be called at least once during node creation
        mock_getrandbits.assert_called_with(64)

    def test_get_machine_id_through_node_creation(self):
        """Test __getMachineID static method through node creation"""
        node = Node("test_node")
        
        # Currently always returns 0
        self.assertEqual(node.info.machine_id, 0)

    def test_node_integration_flow(self):
        """Test complete node lifecycle integration"""
        node = Node("integration_test")
        
        # Verify node is properly initialized
        self.assertTrue(node.ok())
        self.assertTrue(node.registered_flag)
        
        # Create various components
        mock_msg = MockMessage()
        pub = node.create_publisher(lambda: mock_msg, "/test_topic")
        sub = node.create_subscriber(lambda: mock_msg, "/test_topic", Mock())
        timer = node.create_timer(1.0, Mock())
        
        # Verify components are tracked
        self.assertEqual(len(node.components), 3)
        
        # Test shutdown
        node.shutdown()
        self.assertFalse(node.ok())


if __name__ == '__main__':
    unittest.main()