(define (problem robot-charging-problem)
  (:domain robot-charging)
  (:objects
    robot - robot
    charging-station - charging-station
    obstacle - obstacle
    battery - battery
  )
  (:init
    (at robot charging-station)
    (on-ground battery charging-station)
    (blocked obstacle charging-station)
    (at robot charging-station)
    (on-ground battery charging-station)
    (blocked obstacle charging-station)
  )
  (:goal
    (and (recharged battery) (at robot charging-station))
  )
)