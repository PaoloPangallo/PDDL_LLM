(define (problem astronaut_sample_mission)
  (:domain astronaut_mission)
  (:objects astronaut - agent rover - object base - location crater - location sample - object) ; Added 'sample' to objects
  (:init (at astronaut base)
         (at rover base)
         (at sample crater)) ; Corrected the initial state for 'sample' being at 'crater'
  (:goal (and (at astronaut base)
              (has astronaut sample)))) ; Added the goal fact to indicate that the astronaut has the sample