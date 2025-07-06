(define (problem robot-recharge)
  (:domain charging-station)
  (:objects 
    robot 
    battery 
    charging-station 
    obstacle)
  (:init 
    (at robot charging-station)
    (on-ground battery charging-station)
    (on-ground obstacle charging-station)
    (carrying robot battery)
    (not (sleeping robot charging-station)))
  (:goal 
    (and (at robot charging-station) (not (on-ground obstacle charging-station)))))