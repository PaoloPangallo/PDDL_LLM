(define (problem world_exploration))
  (domain world_travel)
  (:objects start town1 town2 town3 person1)
  (:init
    (at person1 start)
    (nearby start town1)
    (visible start)
  )
  (:goal (and (at person1 town3) (confirmed_visible town3)))