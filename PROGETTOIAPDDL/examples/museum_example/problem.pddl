(define (problem museum-security-prob)
  (:domain museum-security)
  (:objects
    robot - agent
    station room1 room2 room3 - location
    sensor - tool
  )
  (:init
    (at robot station)
    (charged robot)
    (available sensor)
    ; nessuna stanza è ancora scansionata
  )
  (:goal (and
    (scanned room1)
    (scanned room2)
    (scanned room3)
    (at robot station)
    (charged robot)
  ))
)
