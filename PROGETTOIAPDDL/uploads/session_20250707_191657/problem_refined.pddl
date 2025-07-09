(define (problem rover-problem)
  (:domain rover-domain)
  (:objects base crater sample astronaut - agent) ; Added "agent" type for ?a
  (:init (at astronaut base ?base) ; Corrected from "(at astronaut)" to include location
         (at rover base ?base)    ; Corrected from "(at rover)" to include location
         (at sample crater ?crater)) ; Corrected from "(at sample)" to include location
  (:goal (and (at astronaut base ?base) ; Ensure goal uses the correct object type and variable
              (has astronaut sample)))
)