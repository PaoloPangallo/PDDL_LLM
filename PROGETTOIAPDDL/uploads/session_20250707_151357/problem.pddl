(define (problem astro-collect-prob)
  (:domain astro-collect)
  (:objects base crater sample astronaut rover)
  (:init
    (at astronaut base)
    (at rover base)
    (at sample crater))
  (:goal
    (and
      (at astronaut base)
      (has astronaut sample)))
)