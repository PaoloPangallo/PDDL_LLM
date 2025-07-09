(define (problem example-problem)
  (:domain example)
  (:objects
    a - object
    room1 - location
    room2 - location
  )
  (:init
    (at a room1)
    (free a)
  )
  (:goal (and (at a room2)))
)