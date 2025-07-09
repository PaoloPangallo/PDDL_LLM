(define (problem astronaut_sample_collection)
  (:domain astronaut_mission)
  (:objects base crater sample astronaut rover)
  (:init (at astronaut base)
         (at rover base)
         (at sample crater)) ; Corrected object type
  (:goal (and (at astronaut base)
              (has astronaut sample)))
)