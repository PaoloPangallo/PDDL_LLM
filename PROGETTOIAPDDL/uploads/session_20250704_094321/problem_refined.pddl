(define (problem robot-problem)
  (:domain robot-domain)
  (:objects
    robot - robot
    charging-station - charging-station
    obstacle - obstacle
    battery - battery
    ground - ground)
  (:init
    (at robot charging-station)
    (on-ground battery charging-station)
    (blocked obstacle charging-station)
    (recharged battery))
  (:goal
    (and (recharged battery) (at robot charging-station))))