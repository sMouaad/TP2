import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from turtlesim.msg import Pose
from turtlesim.srv import SetPen
from std_msgs.msg import String
import math

# Limites du mur
WALL_MIN = 0.5
WALL_MAX = 11.09 - 0.5

SPEED = 2.0
TURN_SPEED = 4.0
ARRIVAL_THRESHOLD = 0.2

# Coins du rectangle (sens anti-horaire)
CORNERS_CCW = [
    (WALL_MIN, WALL_MIN),   # bas gauche
    (WALL_MAX, WALL_MIN),   # bas droite
    (WALL_MAX, WALL_MAX),   # haut droite
    (WALL_MIN, WALL_MAX),   # haut gauche
]

class TurtleBoundary(Node):

    def __init__(self):
        super().__init__('turtle_boundary')

        self.pose = None
        self.start_pose = None
        self.return_home = False

        self.boundary_started = False 
        self.corner_index = 0

        
        self.sub = self.create_subscription(
            Pose,
            '/turtle1/pose',
            self.pose_callback,
            10)
        
        self.pub = self.create_publisher(
            Twist,
            '/turtle1/cmd_vel',
            10)

        self.pen_client = self.create_client(SetPen, '/turtle1/set_pen')

        self.timer = self.create_timer(0.02, self.control_loop)

        self.get_logger().info("Node started")

        # stylo levé au début (ne pas dessiner du centre au mur)
        self._set_pen(off=True)
        
        #Added for keyboard listener
        self.manual_mode = False
        self.last_cmd = None

        self.key_sub = self.create_subscription(
            String,
            '/keyboard_input',
            self.key_callback,
            10
        )


    def pose_callback(self, msg):
        self.pose = msg

        if self.start_pose is None:
            self.start_pose = (msg.x, msg.y)


    def control_loop(self):
        
        #Mode manuel
        if self.manual_mode:
            twist = Twist()

            if self.last_cmd == 'forward':
                twist.linear.x = SPEED

            elif self.last_cmd == 'backward':
                twist.linear.x = -SPEED

            elif self.last_cmd == 'left':
                twist.angular.z = TURN_SPEED

            elif self.last_cmd == 'right':
                twist.angular.z = -TURN_SPEED

            self.pub.publish(twist)
            return
        

        if self.pose is None:
            return

        twist = Twist()

        # Retour au point de départ
        if self.return_home:
            if self._go_to(self.start_pose[0], self.start_pose[1], twist):
                twist.linear.x = 0.0
                twist.angular.z = 0.0
                self.get_logger().info("Retour au centre terminé")
                self.timer.cancel()

            self.pub.publish(twist)
            return

        # Aller au premier mur sans dessiner
        if not self.boundary_started:

            target = CORNERS_CCW[0]

            if self._go_to(target[0], target[1], twist):

                self.boundary_started = True
                self.corner_index = 1 #Passer au coin suivant

                # Commencer à dessiner
                self._set_pen(off=False)

            self.pub.publish(twist)
            return

        # A chaque tick du timer
        # Suivre les coins du rectangle
        target = CORNERS_CCW[self.corner_index]

        if self._go_to(target[0], target[1], twist):

            self.corner_index += 1

            # après le 4e coin, revenir au 1er pour fermer
            if self.corner_index == len(CORNERS_CCW):
                self.corner_index = 0

            # après avoir refait le premier coin, retour maison
            elif self.corner_index == 1:
                self._set_pen(off=True)
                self.return_home = True

        self.pub.publish(twist)


    def _go_to(self, x, y, twist):
        # Cible - pos actuelle
        dx = x - self.pose.x
        dy = y - self.pose.y

        distance = math.sqrt(dx*dx + dy*dy)

        if distance < ARRIVAL_THRESHOLD: #il lui reste moins de 0.2, donc stop
            twist.linear.x = 0.0
            twist.angular.z = 0.0
            return True

        desired_theta = math.atan2(dy, dx)
        angle_error = self._normalize(desired_theta - self.pose.theta) 

        if abs(angle_error) > 0.2: #Mauvaise direction, tourner sur place, ne plus avancer
            twist.linear.x = 0.0
            twist.angular.z = angle_error * TURN_SPEED
        else: #Si bonne direction, avance plus vite si loin
            twist.linear.x = min(distance * SPEED, SPEED)
            twist.angular.z = max(min(angle_error * TURN_SPEED, SPEED), -SPEED)

        return False
    
    #Convertit un angle pour qu’il soit toujours dans [-pi, pi]
    def _normalize(self, angle):

        while angle > math.pi:
            angle -= 2 * math.pi

        while angle < -math.pi:
            angle += 2 * math.pi

        return angle


    def _set_pen(self, r=255, g=0, b=0, width=3, off=False):

        if not self.pen_client.wait_for_service(timeout_sec=1.0):
            return

        req = SetPen.Request()
        req.r = r
        req.g = g
        req.b = b
        req.width = width
        req.off = int(off)

        self.pen_client.call_async(req)

    def key_callback(self, msg):

        if msg.data == 'toggle_manual': #espace
            self.manual_mode = not self.manual_mode
            self.get_logger().info(f"Manual mode: {self.manual_mode}")
            return

        self.last_cmd = msg.data #si non on stocke la derniere cmd
def main(args=None):

    rclpy.init(args=args)

    node = TurtleBoundary()

    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()