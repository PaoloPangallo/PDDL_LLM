(define (problem pc-assembly-prob)
  (:domain pc-assembly)
  (:objects
    tech   - agent
    cpu ram disk  - component
    workbench office  - location
  )
  (:init
    (at tech office)
    ; inizialmente non ha componenti
  )
  (:goal (and
    (mounted cpu)
    (mounted ram)
    (mounted disk)
    (at tech workbench)
  ))
)
