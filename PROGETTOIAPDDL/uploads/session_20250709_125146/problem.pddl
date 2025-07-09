(define (problem astronaut_sample_mission)
  (:domain astronaut_mission)
  (:objects
    astronaut base crater rover sample
  )
  (:init
    (at astronaut base)
    (at rover base)
    (at sample crater)
  )
  (:goal (and
    (at astronaut base)
    (has astronaut sample)
  ))
)