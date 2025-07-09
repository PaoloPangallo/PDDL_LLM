(define (problem sample-collection-problem)
  (:domain sample-collection)
  (:objects base crater rover astronaut sample)
  (:init
    (at astronaut base)
    (at rover base)
    (at sample crater))
  (:goal
    (and (at astronaut base) (has astronaut sample)))
)