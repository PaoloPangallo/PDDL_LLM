(define (problem example-robot-problem)
  (:domain example-robot)
  (:objects robot battery charging_station some_location - location obstacle - obstacle)
  (:init
    (at robot some_location)
    (on_ground battery charging_station)
    (blocked obstacle charging_station))
  (:goal
    (and
      (at robot charging_station)
      (charged battery)))
)