(define (problem space-mission-problem)
  (:domain space-mission)
  (:objects base crater sample astronaut rover)
  (:init
    (at astronaut base)
    (at rover base)
    (at sample crater)
    (at astronaut crate)
    (in astronaut rover))
  (:goal
    (and
      (at astronaut base)
      (has astronaut sample)))
)