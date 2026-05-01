"""
Description
"""
import random
from typing import Any, List

import cv2
import numpy as np
from enum import Enum
from controller import Robot



# --- PARAMETERS ---

TIME_STEP = 64
DEBUG_FLAG = True

### Red is around 0 and 180 in HSV ###
RED_ARROW_LOWER_COLOR_1 = np.array([0, 100, 70])
RED_ARROW_UPPER_COLOR_1 = np.array([10, 255, 255])
RED_ARROW_LOWER_COLOR_2 = np.array([170, 100, 70])
RED_ARROW_UPPER_COLOR_2 = np.array([180, 255, 255])

### Blue HSV ###
BLUE_ARROW_LOWER_COLOR = np.array([85, 100, 70])
BLUE_ARROW_UPPER_COLOR = np.array([135, 255, 255])

### Arrow detection offset percentage
ARROW_OFFSET_PERCENTAGE = 0.1

### Control Thresholds
ARROW_AREA_THRESHOLD = 45000
DIRECTION_DETECTION_THRESHOLD = 16000
ROTATION_CORRECTION_DISTANCE_THRESHOLD = 16000

# - END OF PARAMETERS -


class Direction(Enum):
    LEFT = -1
    UNKNOWN = 0
    RIGHT = 1


class RotationCommand(Enum):
    CORRECT_LEFT = -2   # Small left rotation to keep the arrow at the center
    LEFT = -1           # 90 degree left
    NO_ROTATION = 0
    RIGHT = 1           # 90 degree right
    CORRECT_RIGHT = 2   # # Small right rotation to keep the arrow at the center


class MovementCommand(Enum):
    BACKWARD = -1
    STOP = 0
    FORWARD = 1


class ControlCommand:
    def __init__(self):
        self.rotation: RotationCommand = RotationCommand.NO_ROTATION
        self.movement: MovementCommand = MovementCommand.STOP
        self.correction_factor: float = 0.0  # [0.0, 1.0]


class ControlLogic:
    """
    ControlLogic represents a statemachine to provide the proper control commands.
    """

    def __init__(self):
        self.target_direction: Direction = Direction.UNKNOWN

    def calculate_command(self, estimated_distance: float, estimated_direction: Direction, x_offset_normalized: float) -> ControlCommand:

        cmd = ControlCommand()

        if estimated_distance < DIRECTION_DETECTION_THRESHOLD:
            if estimated_direction != Direction.UNKNOWN: self.target_direction = estimated_direction

        if self.target_direction == Direction.UNKNOWN:
            cmd.movement = MovementCommand.FORWARD
            cmd.rotation = RotationCommand.NO_ROTATION
            return cmd

        if estimated_distance > ARROW_AREA_THRESHOLD:
            cmd.movement = MovementCommand.STOP
            if self.target_direction == Direction.LEFT: cmd.rotation = RotationCommand.LEFT
            elif self.target_direction == Direction.RIGHT: cmd.rotation = RotationCommand.RIGHT
            self.target_direction = Direction.UNKNOWN
        else:
            cmd.movement = MovementCommand.FORWARD

            ### VISUAL SERVOING ###
            if 0 < estimated_distance < ROTATION_CORRECTION_DISTANCE_THRESHOLD:

                distance_factor = 1.0 - (estimated_distance / ROTATION_CORRECTION_DISTANCE_THRESHOLD)
                distance_factor = max(0.0, min(1.0, distance_factor))

                margin = 0.15

                if x_offset_normalized < -margin:
                    cmd.rotation = RotationCommand.CORRECT_LEFT
                    cmd.correction_factor = distance_factor * abs(x_offset_normalized)
                elif x_offset_normalized > margin:
                    cmd.rotation = RotationCommand.CORRECT_RIGHT
                    cmd.correction_factor = distance_factor * abs(x_offset_normalized)
                else:
                    cmd.rotation = RotationCommand.NO_ROTATION
            else:
                cmd.rotation = RotationCommand.NO_ROTATION

        return cmd


class DistanceEstimator:
    """
    DistanceEstimator provides estimation of the distance between the camera and the arrow.
    """

    def __init__(self):
        self.detected_distance: float = 0.0

    def estimate(self, image, arrow_contour) -> float:
        debug_img = image.copy()

        if arrow_contour is not None:
            self.detected_distance = float(cv2.contourArea(arrow_contour))

            cv2.drawContours(debug_img, [arrow_contour], -1, (0, 255, 0), 2)
            cv2.putText(debug_img, f"Area: {self.detected_distance:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Distance Estimator - Contours", debug_img)

        # The area of the arrow contour can be used as a "distance"
        return self.detected_distance


class DirectionEstimator:
    def __init__(self):
        self.detected_direction: Direction = Direction.UNKNOWN

    def detect_arrow_contour(self, image):
        """
        OpenCV HSV filtering for detecting arrow contours and estimating the direction.
        Ignores the top ARROW_OFFSET_PERCENTAGE [%] of the image.
        """
        height, width, _ = image.shape
        crop_y = int(height * ARROW_OFFSET_PERCENTAGE)
        cropped_image = image[crop_y:height, 0:width]

        hsv = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2HSV)

        # Create masks for hsv color red
        red_mask1 = cv2.inRange(hsv, RED_ARROW_LOWER_COLOR_1, RED_ARROW_UPPER_COLOR_1)
        red_mask2 = cv2.inRange(hsv, RED_ARROW_LOWER_COLOR_2, RED_ARROW_UPPER_COLOR_2)
        red_mask = red_mask1 | red_mask2

        # Create mask for hsv color blue
        mask_blue = cv2.inRange(hsv, BLUE_ARROW_LOWER_COLOR, BLUE_ARROW_UPPER_COLOR)

        # Find the contours for red and blue arrows
        contours_red, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours_blue, _ = cv2.findContours(mask_blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        largest_red = max(contours_red, key=cv2.contourArea) if contours_red else None
        largest_blue = max(contours_blue, key=cv2.contourArea) if contours_blue else None

        area_red = cv2.contourArea(largest_red) if largest_red is not None else 0
        area_blue = cv2.contourArea(largest_blue) if largest_blue is not None else 0

        if area_red == 0 and area_blue == 0:
            self.detected_direction = Direction.UNKNOWN
            return None

        selected_contour = largest_red if area_red > area_blue else largest_blue
        selected_contour[:, 0, 1] += crop_y

        if area_red > area_blue: self.detected_direction = Direction.LEFT
        else: self.detected_direction = Direction.RIGHT

        return selected_contour


class CameraProcessor:
    def __init__(self, camera):
        self.camera = camera
        self.distance_estimator = DistanceEstimator()
        self.direction_estimator = DirectionEstimator()
        self.control_logic = ControlLogic()
        self.current_distance = 0.0                     # OUTPUT: The estimated distance from the arrow
        self.current_direction = Direction.UNKNOWN      # OUTPUT: The estimated direction of the arrow
        self.control_buffer = ControlCommand()          # OUTPUT: The control command to be executed during the movement

    def process_frame(self, image) -> ControlCommand:
        arrow_contour = self.direction_estimator.detect_arrow_contour(image)

        self.current_distance = self.distance_estimator.estimate(image, arrow_contour)
        self.current_direction = self.direction_estimator.detected_direction

        x_offset_normalized = 0.0
        if arrow_contour is not None:
            x, y, w, h = cv2.boundingRect(arrow_contour)
            center_x = x + (w / 2.0)
            img_center_x = image.shape[1] / 2.0
            x_offset_normalized = (center_x - img_center_x) / img_center_x  # [-1.0 .. 1.0]; Negative: Left, Positive: Right

        self.control_buffer = self.control_logic.calculate_command(
            self.current_distance,
            self.current_direction,
            x_offset_normalized
        )

        return self.control_buffer



"""
TEST CODE
"""

if DEBUG_FLAG:
    import time
    import matplotlib.pyplot as plt


class Signal:
    def __init__(self, signal_name: str, signal_reference: Any, min_value: int | float = None, max_value: int | float = None) -> None:
        self.signal_name = signal_name
        self.signal_reference = signal_reference
        self.min_value = min_value
        self.max_value = max_value


def plot_variables(signals: List[Signal] = None, window_size: int = 50) -> None:
    """Plotting signals realtime"""
    if not signals:
        return

    if not hasattr(plot_variables, "is_initialized"):
        plt.ion()
        num_signals = len(signals)

        fig, axs = plt.subplots(num_signals, 1, figsize=(8, 1.5 * num_signals), sharex=True)
        if num_signals == 1:
            axs = [axs]

        plot_variables.fig = fig
        plot_variables.axs = axs
        plot_variables.lines = []
        plot_variables.x_data = []
        plot_variables.y_data = [[] for _ in range(num_signals)]
        plot_variables.step = 0

        colors = ['blue', 'red', 'green', 'purple']

        for i, sig in enumerate(signals):
            line, = axs[i].plot([], [], color=colors[i % len(colors)], linestyle='-')
            plot_variables.lines.append(line)

            axs[i].set_ylabel(sig.signal_name, fontweight='bold', fontsize=8)
            axs[i].grid(True, linestyle='--', alpha=0.7)
            axs[i].tick_params(axis='both', which='major', labelsize=8)

            if sig.min_value is not None and sig.max_value is not None:
                margin = max(0.5, (sig.max_value - sig.min_value) * 0.1)
                axs[i].set_ylim(sig.min_value - margin, sig.max_value + margin)
            else:
                axs[i].set_ylim(-0.5, 2.5)

        axs[-1].set_xlabel('Cycle time (Step)', fontsize=9)
        fig.suptitle("Real-time control_buffer signals", fontsize=10)
        fig.tight_layout()

        plot_variables.is_initialized = True
        print("Real-time plot started. Press Ctrl+C to stop, or just close the window.")

    current_step = plot_variables.step
    plot_variables.x_data.append(current_step)

    for i, sig in enumerate(signals):
        val = sig.signal_reference.value if isinstance(sig.signal_reference, Enum) else sig.signal_reference
        plot_variables.y_data[i].append(val)

    if len(plot_variables.x_data) > window_size:
        plot_variables.x_data = plot_variables.x_data[-window_size:]
        for i in range(len(signals)):
            plot_variables.y_data[i] = plot_variables.y_data[i][-window_size:]

    for i in range(len(signals)):
        plot_variables.lines[i].set_data(plot_variables.x_data, plot_variables.y_data[i])

    for ax in plot_variables.axs:
        ax.set_xlim(max(0, current_step - window_size), max(window_size, current_step + 5))

    plot_variables.fig.canvas.draw()
    plot_variables.fig.canvas.flush_events()

    plot_variables.step += 1


def e_puck_movement(left_motor, right_motor, prox_sensors, control_command: ControlCommand, time_step: int):
    """
    Állapotgépes mozgásvezérlés. Ha a robot fordulni kezd,
    a fordulást megszakítás nélkül befejezi.
    """
    MAX_SPEED = 6.28
    base_speed = 0.5 * MAX_SPEED

    # Inicializáljuk a "blokkoló" állapotváltozókat az első futáskor
    if not hasattr(e_puck_movement, "turn_steps_remaining"):
        e_puck_movement.turn_steps_remaining = 0
        e_puck_movement.turn_direction = 0  # 1: Jobb, -1: Bal

    # ==========================================
    # 1. FOLYAMATBAN LÉVŐ FORDULÁS KEZELÉSE
    # ==========================================
    if e_puck_movement.turn_steps_remaining > 0:
        # Csökkentjük a hátralévő lépések számát
        e_puck_movement.turn_steps_remaining -= 1

        # A motorokat a megfelelő irányba pörgetjük
        if e_puck_movement.turn_direction == -1:  # BALRA
            left_motor.setVelocity(-base_speed)
            right_motor.setVelocity(base_speed)
        elif e_puck_movement.turn_direction == 1:  # JOBBRA
            left_motor.setVelocity(base_speed)
            right_motor.setVelocity(-base_speed)

        # AZONNAL VISSZATÉRÜNK! Ignoráljuk a kamerát és a szenzorokat, amíg a fordulás tart.
        return

    # ==========================================
    # 2. ÚJ FORDULÁSI PARANCS FOGADÁSA (Csak teljes fordulásnál!)
    # ==========================================
    if control_command is not None:
        if control_command.rotation in [RotationCommand.LEFT, RotationCommand.RIGHT]:
            # Kb. 0.65 másodperc kell egy 90 fokos forduláshoz ezen a sebességen.
            turn_duration_sec = 0.65
            e_puck_movement.turn_steps_remaining = int((turn_duration_sec * 1000) / time_step)

            if control_command.rotation == RotationCommand.LEFT:
                e_puck_movement.turn_direction = -1
            elif control_command.rotation == RotationCommand.RIGHT:
                e_puck_movement.turn_direction = 1

            return  # Kilépünk, a tényleges forgás a következő lépésben kezdődik

    # ==========================================
    # 3. ALAPÉRTELMEZETT MOZGÁS (Akadálykerülés / Előre haladás)
    # ==========================================
    left_speed = base_speed
    right_speed = base_speed

    front_right_val = prox_sensors[0].getValue()
    front_left_val = prox_sensors[7].getValue()
    side_right_val = prox_sensors[1].getValue()
    side_left_val = prox_sensors[6].getValue()

    front_obstacle = front_right_val > 150.0 or front_left_val > 150.0
    left_obstacle = side_left_val > 150.0
    right_obstacle = side_right_val > 150.0

    if front_obstacle or left_obstacle:
        left_speed = base_speed
        right_speed = -base_speed
    elif right_obstacle:
        left_speed = -base_speed
        right_speed = base_speed

    if control_command is not None and control_command.movement == MovementCommand.FORWARD:
        if not front_obstacle:
            left_speed = base_speed
            right_speed = base_speed

            # --- CORRECTION OF THE DIRECTION OF THE E-PUCK ---
            if control_command.rotation == RotationCommand.CORRECT_LEFT:
                correction = base_speed * control_command.correction_factor
                left_speed -= correction
                right_speed += correction
            elif control_command.rotation == RotationCommand.CORRECT_RIGHT:
                correction = base_speed * control_command.correction_factor
                left_speed += correction
                right_speed -= correction

    left_motor.setVelocity(left_speed)
    right_motor.setVelocity(right_speed)


def main():

    robot = Robot()
    time_step = int(robot.getBasicTimeStep())
    camera_ref = robot.getDevice('camera')

    camera_ref.enable(time_step)
    processor = CameraProcessor(camera=camera_ref)

    # --- INITIALIZE E-PUCK HARDWARE ELEMENTS ---
    left_motor = robot.getDevice('left wheel motor')
    right_motor = robot.getDevice('right wheel motor')
    left_motor.setPosition(float('inf'))
    right_motor.setPosition(float('inf'))
    left_motor.setVelocity(0.0)
    right_motor.setVelocity(0.0)

    prox_sensors = []
    for i in range(8):
        sensor_name = f'ps{i}'
        sensor = robot.getDevice(sensor_name)
        sensor.enable(time_step)
        prox_sensors.append(sensor)
    # -------------------------------------------


    while robot.step(time_step) != -1:


        raw_image = camera_ref.getImage()

        if raw_image is not None:
            width = camera_ref.getWidth()
            height = camera_ref.getHeight()

            img_array = np.frombuffer(raw_image, np.uint8).reshape((height, width, 4))

            cv2_image = img_array[:, :, :3]

            cmd = processor.process_frame(cv2_image)

            cv2.waitKey(1)

            e_puck_movement(left_motor, right_motor, prox_sensors, cmd, time_step)

            # --- VISUALIZE CONTROL SIGNALS ---
            plot_variables(
                signals=[
                    Signal('Ctrl Buff Rotation', cmd.rotation, -2, 2),
                    Signal('Ctrl Buff Movement', cmd.movement, -1, 1),
                    Signal('Estimated Distance', processor.current_distance, -1, 60000),
                    Signal('Estimated Direction', processor.current_direction, -1, 1),
                ],
                window_size=50,
            )
            # ---------------------------------


if __name__ == "__main__":
    DEBUG_FLAG and main()


"""
END OF TEST CODE
"""