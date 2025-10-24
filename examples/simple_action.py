from rix.core import Node
from rix.msg.standard import Double, Float
from math import factorial

max_iters = 10
current_iter = 0
value = 0.0

def exponent(goal: Double, feedback: Float, result: Double) -> bool:
    global current_iter, max_iters, value
    # Taylor series expansion for e^x
    if current_iter >= max_iters:
        result.data = value
        print("Action completed with result: " + str(result.data))
        current_iter = 0
        value = 0.0
        return True  # Indicate completion
    
    term = (goal.data ** current_iter) / factorial(current_iter)
    value += term
    feedback.data = value
    print(f"Iteration {current_iter}: feedback = {feedback.data}")
    current_iter += 1
    return False  # Indicate not yet complete

def main():
    node = Node("simple_action")
    if not node.ok():
        print("Failed to initialize node")
        return

    act = node.create_action(Double, Float, Double, "/exponent", exponent)
    if not act.ok():
        print("Failed to advertise action")
        return
    
    def goal_callback() -> None:
        global current_iter, value
        current_iter = 0
        value = 0.0
        print("New goal received")
    act.set_goal_callback(goal_callback)

    def preempt_callback() -> None:
        global current_iter, value
        print("Goal preempted")
        current_iter = 0
        value = 0.0
    act.set_preempt_callback(preempt_callback)
    
    try:
        node.spin()
    except KeyboardInterrupt as e:
        return


if __name__ == "__main__":
    main()
