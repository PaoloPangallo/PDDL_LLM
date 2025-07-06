(define (problem robot-recharge)
  (:domain charging-station)
  (:objects 
    robot 
    battery 
    charging-station 
    obstacle
    robot-1 
    battery-1 
    charging-station-1 
    obstacle-1)
  (:init 
    (at robot-1 charging-station-1)
    (on-ground battery-1 charging-station-1)
    (on-ground obstacle-1 charging-station-1)
    (carrying robot-1 battery-1))
  (:goal 
    (and (at robot-1 charging-station-1) (not (on-ground obstacle-1 charging-station-1)))))