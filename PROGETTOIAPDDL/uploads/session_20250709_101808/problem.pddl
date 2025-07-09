(define (problem my-problem)
  (:domain my-domain)
  (:objects
    robot - agent
    charging_station some_location - location
    battery obstacle - object
  )
  (:init
    (at robot some_location)
    (on_ground battery charging_station)
    (blocked obstacle charging_station)
  )
  (:goal (and (at robot charging_station) (charged battery)))
)