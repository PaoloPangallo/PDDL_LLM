(define (problem robot-reach-charging-station)
  (:domain robot-reach-charging-station)
  (:objects 
    robot 
    battery 
    charging-station 
    obstacle)
  (:init 
    (at robot charging-station)
    (on-ground battery charging-station)
    (on-ground obstacle charging-station)
    (at robot charging-station)
    (on-ground battery charging-station)
    (on-ground obstacle charging-station))
  (:goal 
    (and (at robot charging-station) (not (on-ground obstacle charging-station)) (at robot charging-station) (not (on-ground obstacle charging-station)))))