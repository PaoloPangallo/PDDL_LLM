(define (problem sample_mission)
  (:domain space_mission)
  (:objects base crater astronaut rover sample)
  (:init
    (at astronaut base)
    (at rover base)
    (at sample crater))
  (:goal
    (and
      (at astronaut base)
      (has astronaut sample)))
)