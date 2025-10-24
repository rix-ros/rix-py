from rix.core import Node, TimerCallback
from rix.msg.standard import Float, Double


def main():
    node = Node("simple_action_client")
    if not node.ok():
        print("Failed to initialize node")
        return

    action_client = node.create_action_client(Double, Float, Double, "/exponent")
    if not action_client.ok():
        print("Failed to create action client")
        return

    def result_callback(result: Double) -> None:
        print("Final result received: " + str(result.data))

    action_client.set_result_callback(Double, result_callback)

    def feedback_callback(feedback: Float) -> None:
        print("Feedback received: " + str(feedback.data))

    action_client.set_feedback_callback(Float, feedback_callback)

    i: int = 0

    def timer_callback(event: TimerCallback.Event) -> None:
        nonlocal i
        goal = Double()
        goal.data = i
        action_client.dispatch(goal)
        print(f"Goal: {goal.data}")
        i += 1

    node.create_timer(1, timer_callback)
    node.spin()


if __name__ == "__main__":
    main()
