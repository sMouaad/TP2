import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from irobot_create_msgs.action import Undock
import math

# Namespace du robot
ROBOT_NS = '/Robot5'

# Vitesses adaptées pour le vrai Create3
SPEED = 0.2          # m/s (lent pour la sécurité)
TURN_SPEED = 1.0     # rad/s
ARRIVAL_THRESHOLD = 0.15  # mètres

# Rectangle à tracer (coordonnées relatives au point de départ en mètres)
# Le robot roulera un carré de 1.5m x 1.5m
RECT_W = 1.5
RECT_H = 1.5

class TurtleBoundary(Node):

    def __init__(self):
        super().__init__('turtle_boundary')

        # ── État ──
        self.pose_x = 0.0
        self.pose_y = 0.0
        self.pose_theta = 0.0
        self.pose_received = False

        self.start_pose = None
        self.return_home = False
        self.boundary_started = False
        self.corner_index = 0
        self.corners = []

        # ── Undock ──
        self.undocked = False
        self.undock_in_progress = False
        self.undock_client = ActionClient(
            self, Undock, f'{ROBOT_NS}/undock')

        # ── QoS pour Create3 (BEST_EFFORT comme le robot publie) ──
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # ── Subscribers ──
        self.sub = self.create_subscription(
            Odometry,
            f'{ROBOT_NS}/odom',
            self.odom_callback,
            sensor_qos)

        # ── Publisher ──
        self.pub = self.create_publisher(
            Twist,
            f'{ROBOT_NS}/cmd_vel',
            10)

        # ── Control loop ──
        self.timer = self.create_timer(0.05, self.control_loop)

        self.get_logger().info(f"Node started — waiting for {ROBOT_NS}/odom…")

        # ── Mode manuel (keyboard listener) ──
        self.manual_mode = False
        self.last_cmd = None

        self.key_sub = self.create_subscription(
            String,
            '/keyboard_input',
            self.key_callback,
            10
        )

    # ═══════════════════════════════════════════
    # Callbacks
    # ═══════════════════════════════════════════

    def odom_callback(self, msg):
        """Extraire (x, y, yaw) depuis l'Odometry (quaternion → yaw)."""
        self.pose_x = msg.pose.pose.position.x
        self.pose_y = msg.pose.pose.position.y

        # Quaternion → yaw (rotation autour de z)
        q = msg.pose.pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        self.pose_theta = math.atan2(siny_cosp, cosy_cosp)

        if not self.pose_received:
            self.pose_received = True
            self.get_logger().info(
                f"Première pose reçue: x={self.pose_x:.2f}, y={self.pose_y:.2f}, θ={self.pose_theta:.2f}")

    def key_callback(self, msg):
        if msg.data == 'toggle_manual':
            self.manual_mode = not self.manual_mode
            self.get_logger().info(f"Manual mode: {self.manual_mode}")
            if self.manual_mode:
                # Arrêter le robot immédiatement
                self.pub.publish(Twist())
            return
        self.last_cmd = msg.data

    # ═══════════════════════════════════════════
    # Undock
    # ═══════════════════════════════════════════

    def _start_undock(self):
        """Envoyer l'action Undock au Create3."""
        if not self.undock_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error(
                f"Undock action server {ROBOT_NS}/undock non disponible!")
            return

        self.get_logger().info("Envoi de l'action Undock…")
        self.undock_in_progress = True

        goal = Undock.Goal()
        future = self.undock_client.send_goal_async(goal)
        future.add_done_callback(self._undock_goal_response)

    def _undock_goal_response(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn("Undock goal rejeté — peut-être déjà undocké?")
            self.undocked = True
            self.undock_in_progress = False
            return

        self.get_logger().info("Undock goal accepté, en cours…")
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._undock_result)

    def _undock_result(self, future):
        self.get_logger().info("✅ Undock terminé!")
        self.undocked = True
        self.undock_in_progress = False

    # ═══════════════════════════════════════════
    # Boucle de contrôle principale
    # ═══════════════════════════════════════════

    def control_loop(self):

        # Mode manuel — ijkl pilotage
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

        # Attendre la première pose
        if not self.pose_received:
            return

        # ── Étape 1 : Undock ──
        if not self.undocked:
            if not self.undock_in_progress:
                self._start_undock()
            return

        # ── Calculer les coins au premier passage après undock ──
        if not self.corners:
            self.start_pose = (self.pose_x, self.pose_y)
            sx, sy = self.start_pose
            self.corners = [
                (sx,          sy),            # départ (coin bas-gauche)
                (sx + RECT_W, sy),            # coin bas-droite
                (sx + RECT_W, sy + RECT_H),   # coin haut-droite
                (sx,          sy + RECT_H),   # coin haut-gauche
            ]
            self.corner_index = 1  # le robot est déjà au coin 0
            self.get_logger().info(
                f"Rectangle défini: {self.corners}")

        twist = Twist()

        # ── Retour au point de départ ──
        if self.return_home:
            if self._go_to(self.start_pose[0], self.start_pose[1], twist):
                twist.linear.x = 0.0
                twist.angular.z = 0.0
                self.get_logger().info("✅ Retour au point de départ terminé")
                self.timer.cancel()
            self.pub.publish(twist)
            return

        # ── Aller au premier coin ──
        if not self.boundary_started:
            target = self.corners[0]
            if self._go_to(target[0], target[1], twist):
                self.boundary_started = True
                self.corner_index = 1
                self.get_logger().info("Début du tracé du rectangle")
            self.pub.publish(twist)
            return

        # ── Suivre les coins du rectangle ──
        target = self.corners[self.corner_index]

        if self._go_to(target[0], target[1], twist):
            self.get_logger().info(
                f"Coin {self.corner_index} atteint: ({target[0]:.2f}, {target[1]:.2f})")
            self.corner_index += 1

            # Après le 4e coin, revenir au 1er pour fermer
            if self.corner_index == len(self.corners):
                self.corner_index = 0

            # Après avoir refait le premier coin, retour maison
            elif self.corner_index == 1:
                self.return_home = True
                self.get_logger().info("Rectangle terminé, retour au départ…")

        self.pub.publish(twist)

    # ═══════════════════════════════════════════
    # Navigation point-à-point
    # ═══════════════════════════════════════════

    def _go_to(self, x, y, twist):
        """Naviguer vers (x, y). Retourne True si arrivé."""
        dx = x - self.pose_x
        dy = y - self.pose_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < ARRIVAL_THRESHOLD:
            twist.linear.x = 0.0
            twist.angular.z = 0.0
            return True

        desired_theta = math.atan2(dy, dx)
        angle_error = self._normalize(desired_theta - self.pose_theta)

        if abs(angle_error) > 0.3:
            # Mauvaise direction → tourner sur place
            twist.linear.x = 0.0
            twist.angular.z = angle_error * TURN_SPEED
        else:
            # Bonne direction → avancer proportionnellement
            twist.linear.x = min(distance * SPEED, SPEED)
            twist.angular.z = max(min(angle_error * TURN_SPEED, SPEED), -SPEED)

        return False

    def _normalize(self, angle):
        """Normaliser un angle dans [-pi, pi]."""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle


def main(args=None):
    rclpy.init(args=args)
    node = TurtleBoundary()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()