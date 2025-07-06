(define (problem Battery-Recharge-Problem)
  (:domain Battery-Recharge-Domain)
  (:objects robot - Robot
            charging-station - ChargingStation
            battery - Battery
            obstacle - Obstacle)
  (:init (at robot ?location)
         (on-ground battery ?location)
         (blocked obstacle ?location))
  (:goal (and (at robot charging-station)
              (not (blocked obstacle ?location))))
)