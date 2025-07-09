(define (problem my-problem)
  (:domain my-domain)
  (:objects
    astronaut - agent
    base crater - location
    sample - object
    rover - vehicle
  )
  (:init
    (at astronaut base)
    (at rover base)
    (at sample crater)
  )
  (:goal (and (at astronaut base) (has astronaut sample)))
)