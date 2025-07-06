(define (problem robot-recharge)
  (:domain robot-recharge)
  (:objects 
    robot 
    battery 
    charging-station 
    obstacle 
    at 
    on-ground)
  (:init 
    (at robot charging-station)
    (on-ground battery charging-station)
    (on-ground obstacle charging-station))
  (:goal 
    (and (at robot charging-station) (not (on-ground obstacle charging-station)))))