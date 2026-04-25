from controller import Robot

TIME_STEP = 64
MAX_SPEED = 6.28

# --- Movement States ---
STATE_FORWARD = "FORWARD"
STATE_TURN_LEFT = "TURN_LEFT"
STATE_TURN_RIGHT = "TURN_RIGHT"


TURN_DURATION = 18 

def get_vision_command():
   
    
    return 'RIGHT' 

def main():
    robot = Robot()
    
    # 1. Initialize motors
    left_motor = robot.getDevice('left wheel motor')
    right_motor = robot.getDevice('right wheel motor')
    left_motor.setPosition(float('inf'))
    right_motor.setPosition(float('inf'))
    left_motor.setVelocity(0.0)
    right_motor.setVelocity(0.0)
    
   
    prox_sensors = []
    for i in range(8):
        sensor_name = 'ps' + str(i)
        sensor = robot.getDevice(sensor_name)
        sensor.enable(TIME_STEP)
        prox_sensors.append(sensor)
        
    current_state = STATE_FORWARD
    turn_timer = 0
    
    print("Movement Controller Started. Waiting for vision commands at junctions...")
    
    while robot.step(TIME_STEP) != -1:
        
        front_distance = max(prox_sensors[0].getValue(), prox_sensors[7].getValue())
        
       
        left_wall_close = prox_sensors[5].getValue() > 80
        right_wall_close = prox_sensors[2].getValue() > 80
        
        
        if current_state == STATE_FORWARD:
            
            
            if front_distance > 150: 
                left_motor.setVelocity(0)
                right_motor.setVelocity(0)
                
                
                command = get_vision_command()
                
                if command == 'LEFT':
                    current_state = STATE_TURN_LEFT
                    turn_timer = TURN_DURATION
                elif command == 'RIGHT':
                    current_state = STATE_TURN_RIGHT
                    turn_timer = TURN_DURATION
                    
          
            else:
                left_speed = MAX_SPEED * 0.8
                right_speed = MAX_SPEED * 0.8
                
                
                if left_wall_close:
                    left_speed += 0.5  
                elif right_wall_close:
                    right_speed += 0.5 
                    
                left_motor.setVelocity(left_speed)
                right_motor.setVelocity(right_speed)
                

        elif current_state == STATE_TURN_LEFT:
            if turn_timer > 0:
                left_motor.setVelocity(-MAX_SPEED * 0.5)
                right_motor.setVelocity(MAX_SPEED * 0.5)
                turn_timer -= 1
            else:
                current_state = STATE_FORWARD

        elif current_state == STATE_TURN_RIGHT:
            if turn_timer > 0:
                left_motor.setVelocity(MAX_SPEED * 0.5)
                right_motor.setVelocity(-MAX_SPEED * 0.5)
                turn_timer -= 1
            else:
                current_state = STATE_FORWARD

if __name__ == "__main__":
    main()