import unittest
import numpy as np
import time
from unittest.mock import Mock, patch
from rix.tf.frame_graph import TransformBuffer, FrameGraph, Frame
from rix.msg.geometry import TF, TransformStamped, Transform, Vector3, Quaternion
from rix.msg.standard import Header, Time

class TestTransformBuffer(unittest.TestCase):
    def setUp(self):
        self.buffer = TransformBuffer(duration=1.0)
        self.identity_matrix = np.eye(4)
        self.translation_matrix = np.array([
            [1, 0, 0, 1],
            [0, 1, 0, 2],
            [0, 0, 1, 3],
            [0, 0, 0, 1]
        ])

    def test_initialization(self):
        """Test TransformBuffer initialization"""
        self.assertEqual(self.buffer.duration, 1.0)
        self.assertTrue(self.buffer.empty())
        self.assertEqual(self.buffer.size(), 0)

    def test_insert_single_transform(self):
        """Test inserting a single transform"""
        self.buffer.insert(1.0, self.identity_matrix)
        self.assertFalse(self.buffer.empty())
        self.assertEqual(self.buffer.size(), 1)

    def test_insert_multiple_transforms_ordered(self):
        """Test inserting multiple transforms in chronological order"""
        self.buffer.insert(1.0, self.identity_matrix)
        self.buffer.insert(2.0, self.translation_matrix)
        self.assertEqual(self.buffer.size(), 2)
        
        # Check ordering is maintained
        self.assertEqual(self.buffer.buffer[0][0], 1.0)
        self.assertEqual(self.buffer.buffer[1][0], 2.0)

    def test_insert_multiple_transforms_unordered(self):
        """Test inserting transforms out of chronological order"""
        self.buffer.insert(2.0, self.translation_matrix)
        self.buffer.insert(1.0, self.identity_matrix)
        self.assertEqual(self.buffer.size(), 2)
        
        # Check ordering is maintained after sorting
        self.assertEqual(self.buffer.buffer[0][0], 1.0)
        self.assertEqual(self.buffer.buffer[1][0], 2.0)

    def test_pruning_old_entries(self):
        """Test that old entries are pruned based on duration"""
        # Insert transforms with timestamps spread over 2 seconds
        self.buffer.insert(1.0, self.identity_matrix)
        self.buffer.insert(1.5, self.translation_matrix)
        self.buffer.insert(2.5, self.identity_matrix)  # This should trigger pruning
        
        # Only transforms within 1.0 second of latest (2.5) should remain
        self.assertEqual(self.buffer.size(), 2)
        self.assertEqual(self.buffer.buffer[0][0], 1.5)
        self.assertEqual(self.buffer.buffer[1][0], 2.5)

    def test_get_exact_match(self):
        """Test getting transform with exact timestamp match"""
        self.buffer.insert(1.0, self.translation_matrix)
        result = self.buffer.get(1.0)
        np.testing.assert_array_equal(result, self.translation_matrix)

    def test_get_empty_buffer(self):
        """Test getting transform from empty buffer"""
        result = self.buffer.get(1.0)
        self.assertIsNone(result)

    def test_get_before_earliest(self):
        """Test getting transform before earliest timestamp"""
        self.buffer.insert(2.0, self.translation_matrix)
        result = self.buffer.get(1.0)
        np.testing.assert_array_equal(result, self.translation_matrix)

    def test_get_after_latest(self):
        """Test getting transform after latest timestamp"""
        self.buffer.insert(1.0, self.translation_matrix)
        result = self.buffer.get(2.0)
        np.testing.assert_array_equal(result, self.translation_matrix)

    @patch('rix.tf.frame_graph.interpolate_transform')
    def test_get_interpolation(self, mock_interpolate):
        """Test transform interpolation between two timestamps"""
        mock_interpolate.return_value = self.identity_matrix
        
        self.buffer.insert(1.0, self.identity_matrix)
        self.buffer.insert(1.5, self.translation_matrix)
        
        result = self.buffer.get(1.25)
        
        # Verify interpolation was called with correct parameters
        mock_interpolate.assert_called_once()
        args = mock_interpolate.call_args[0]
        np.testing.assert_array_equal(args[0], self.identity_matrix)
        np.testing.assert_array_equal(args[1], self.translation_matrix)
        self.assertAlmostEqual(args[2], 0.5)  # t parameter should be 0.5

    def test_clear(self):
        """Test clearing the buffer"""
        self.buffer.insert(1.0, self.identity_matrix)
        self.buffer.clear()
        self.assertTrue(self.buffer.empty())
        self.assertEqual(self.buffer.size(), 0)


class TestFrameGraph(unittest.TestCase):
    def setUp(self):
        self.graph = FrameGraph("world", duration=1.0)
        self.transform_stamped = self._create_transform_stamped(
            "world", "base_link", 1.0, [1, 2, 3], [0, 0, 0, 1]
        )

    def _create_transform_stamped(self, parent_frame, child_frame, timestamp, 
                                translation, rotation):
        """Helper to create TransformStamped messages"""
        tf = TransformStamped()
        tf.header.frame_id = parent_frame
        tf.child_frame_id = child_frame
        tf.header.stamp.sec = int(timestamp)
        tf.header.stamp.nsec = int((timestamp - int(timestamp)) * 1e9)
        
        tf.transform.translation.x = translation[0]
        tf.transform.translation.y = translation[1]
        tf.transform.translation.z = translation[2]
        
        tf.transform.rotation.x = rotation[0]
        tf.transform.rotation.y = rotation[1]
        tf.transform.rotation.z = rotation[2]
        tf.transform.rotation.w = rotation[3]
        
        return tf

    def test_initialization(self):
        """Test FrameGraph initialization"""
        self.assertEqual(self.graph.root, "world")
        self.assertTrue(self.graph.exists("world"))
        self.assertEqual(len(self.graph.frames), 1)

    def test_update_from_transform_new_frames(self):
        """Test updating graph with transform between new frames"""
        success = self.graph.update_from_transform(self.transform_stamped)
        self.assertTrue(success)
        self.assertTrue(self.graph.exists("base_link"))
        self.assertEqual(len(self.graph.frames), 2)

    def test_update_from_tf_message(self):
        """Test updating graph from TF message"""
        tf_msg = TF()
        tf_msg.transforms = [self.transform_stamped]
        
        success = self.graph.update_from_tf(tf_msg)
        self.assertTrue(success)
        self.assertTrue(self.graph.exists("base_link"))

    def test_find_frame(self):
        """Test finding frames in the graph"""
        self.graph.update_from_transform(self.transform_stamped)
        
        world_frame = self.graph.find("world")
        self.assertIsNotNone(world_frame)
        self.assertEqual(world_frame.name, "world")
        
        base_frame = self.graph.find("base_link")
        self.assertIsNotNone(base_frame)
        self.assertEqual(base_frame.name, "base_link")
        
        nonexistent = self.graph.find("nonexistent")
        self.assertIsNone(nonexistent)

    def test_get_leaves(self):
        """Test getting leaf frames"""
        self.graph.update_from_transform(self.transform_stamped)
        leaves = self.graph.get_leaves()
        self.assertIn("base_link", leaves)
        self.assertNotIn("world", leaves)

    def test_get_parent_child_relationships(self):
        """Test parent-child relationships"""
        self.graph.update_from_transform(self.transform_stamped)
        
        base_frame = self.graph.find("base_link")
        world_frame = self.graph.find("world")
        
        parent = self.graph.get_parent(base_frame)
        self.assertEqual(parent.name, "world")
        
        children = self.graph.get_children(world_frame)
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0].name, "base_link")

    def test_find_nearest_ancestor_direct(self):
        """Test finding nearest ancestor for direct parent-child"""
        self.graph.update_from_transform(self.transform_stamped)
        ancestor = self.graph.find_nearest_ancestor("base_link", "world")
        self.assertEqual(ancestor, "world")

    def test_find_nearest_ancestor_siblings(self):
        """Test finding nearest ancestor for sibling frames"""
        # Add two children to world
        tf1 = self._create_transform_stamped("world", "child1", 1.0, [1, 0, 0], [0, 0, 0, 1])
        tf2 = self._create_transform_stamped("world", "child2", 1.0, [0, 1, 0], [0, 0, 0, 1])
        
        self.graph.update_from_transform(tf1)
        self.graph.update_from_transform(tf2)
        
        ancestor = self.graph.find_nearest_ancestor("child1", "child2")
        self.assertEqual(ancestor, "world")

    def test_find_nearest_ancestor_no_common(self):
        """Test finding nearest ancestor when no common ancestor exists"""
        # Create separate trees
        tf1 = self._create_transform_stamped("root1", "child1", 1.0, [1, 0, 0], [0, 0, 0, 1])
        tf2 = self._create_transform_stamped("root2", "child2", 1.0, [0, 1, 0], [0, 0, 0, 1])
        
        self.graph.update_from_transform(tf1)
        self.graph.update_from_transform(tf2)
        
        ancestor = self.graph.find_nearest_ancestor("child1", "child2")
        self.assertIsNone(ancestor)

    def test_get_transform_same_frame(self):
        """Test getting transform from frame to itself"""
        result = self.graph.get_transform("world", "world", 1.0)
        np.testing.assert_array_equal(result, np.eye(4))

    def test_get_transform_nonexistent_frame(self):
        """Test getting transform with nonexistent frame"""
        result = self.graph.get_transform("world", "nonexistent", 1.0)
        self.assertIsNone(result)

    @patch('rix.rob.msg_util.transform_to_matrix')
    def test_get_transform_parent_child(self, mock_transform_to_matrix):
        """Test getting transform between parent and child"""
        expected_matrix = np.array([
            [1, 0, 0, 1],
            [0, 1, 0, 2], 
            [0, 0, 1, 3],
            [0, 0, 0, 1]
        ])
        mock_transform_to_matrix.return_value = expected_matrix
        
        self.graph.update_from_transform(self.transform_stamped)
        
        # Mock the buffer.get method to return our expected matrix
        base_frame = self.graph.find("base_link")
        base_frame.buffer.get = Mock(return_value=expected_matrix)
        
        result = self.graph.get_transform("world", "base_link", 1.0)
        
        # The result should be the inverse since we're going from world to base_link
        expected_inverse = np.linalg.inv(expected_matrix)
        np.testing.assert_array_almost_equal(result, expected_inverse)

    def test_complex_frame_chain(self):
        """Test transforms through a chain of frames"""
        # Create chain: world -> base_link -> sensor_link
        tf1 = self._create_transform_stamped("world", "base_link", 1.0, [1, 0, 0], [0, 0, 0, 1])
        tf2 = self._create_transform_stamped("base_link", "sensor_link", 1.0, [0, 1, 0], [0, 0, 0, 1])
        
        self.graph.update_from_transform(tf1)
        self.graph.update_from_transform(tf2)
        
        # Verify all frames exist
        self.assertTrue(self.graph.exists("world"))
        self.assertTrue(self.graph.exists("base_link"))
        self.assertTrue(self.graph.exists("sensor_link"))
        
        # Verify parent-child relationships
        sensor_frame = self.graph.find("sensor_link")
        self.assertEqual(sensor_frame.parent, "base_link")


if __name__ == '__main__':
    unittest.main()