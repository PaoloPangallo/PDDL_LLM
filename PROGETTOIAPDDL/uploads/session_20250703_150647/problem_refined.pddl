(define (problem robot-problem)
  (:domain robot-domain)
  (:objects
    robot - robot
    charging-station - charging-station
    obstacle - obstacle
    battery - battery
    ground - ground
  )
  (:init
    (at robot charging-station)
    (on-ground battery charging-station)
    (blocked obstacle charging-station)
  )
  (:goal
    (and (at robot charging-station) (on-ground battery charging-station) (not (blocked obstacle charging-station)))
  )
)