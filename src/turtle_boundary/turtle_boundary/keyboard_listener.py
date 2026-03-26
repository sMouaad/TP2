import rclpy
from rclpy.node import Node
from std_msgs.msg import String

import sys
import termios
import tty
import select

class KeyboardListener(Node):

    def __init__(self):
        super().__init__('keyboard_listener')

        self.publisher_ = self.create_publisher(
            String,
            '/keyboard_input',
            10)

        """Normalement, le terminal attend qu on appuies sur Entr, donc impossible de lire
        une touche directement. Avec setraw :
        chaque touche est captée instantanement pas besoin d’Entr"""
        
        self.old_settings = termios.tcgetattr(sys.stdin) #Pour restaurer le terminal à la fin
        tty.setraw(sys.stdin.fileno())

        #Vérifier si une touche a été pressée toute les 0.05 sec
        self.timer = self.create_timer(0.05, self.timer_callback)
        
        self.get_logger().info("""
            SPACE toggle manual mode
            i  forward
            k  backward
            j left
            l right
            CTRL+C quit
            """)

    def timer_callback(self):
        #Si une touche a été pressée, la lire, former le msg et le publier pour draw_boundaries
        if select.select([sys.stdin], [], [], 0.0)[0]:
            key = sys.stdin.read(1)

            msg = String()

            if key == ' ':
                msg.data = 'toggle_manual'

            elif key == 'i':
                msg.data = 'forward'

            elif key == 'k':
                msg.data = 'backward'

            elif key == 'j':
                msg.data = 'left'

            elif key == 'l':
                msg.data = 'right'

            elif key == '\x03': #ctrl + C
                raise KeyboardInterrupt

            else:
                return

            self.publisher_.publish(msg)


    def destroy_node(self):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)

    node = KeyboardListener()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()