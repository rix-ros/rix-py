from rix.tf import FrameGraph
from rix.rob import RobotModel

def main():
    json_file = "SimpleBot.json"
    robot = RobotModel(json_file)

    for name, joint in robot.joints.items():
        print(f"Joint: {name}, Type: {joint.type}, Parent: {joint.parent}, Child: {joint.child}, Origin:\n{joint.origin}")

    tf = robot.get_transforms()
    for t in tf.transforms:
        print(t.header.seq)
        print(t.transform.translation.x, t.transform.translation.y, t.transform.translation.z)
        print(t.transform.rotation.x, t.transform.rotation.y, t.transform.rotation.z, t.transform.rotation.w)

    frame_graph = FrameGraph("world")
    frame_graph.update_from_tf(tf)

    for frame_name, frame in frame_graph.frames.items():
        print(f"Frame: {frame_name}, Parent: {frame.parent}, Children: {frame.children}")

    # Test finding nearest common ancestor
    leaves = frame_graph.get_leaves()
    if len(leaves) >= 2:
        ancestor = frame_graph.find_nearest_ancestor(leaves[0], leaves[1])
        print(f"Nearest common ancestor of {leaves[0]} and {leaves[1]} is {ancestor}")

    # Test getting transform between two frames
    if len(leaves) >= 2:
        time = tf.transforms[0].header.stamp.sec + tf.transforms[0].header.stamp.nsec * 1e-9
        transform = frame_graph.get_transform(leaves[0], leaves[1], time)
        if transform is not None:
            print(f"Transform from {leaves[1]} to {leaves[0]} at time {time}:\n{transform}")
        else:
            print(f"No transform found from {leaves[1]} to {leaves[0]} at time {time}")

if __name__ == "__main__":
    main()