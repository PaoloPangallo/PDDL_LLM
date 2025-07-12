(define (domain hero-quest)
  (:requirements :strips)
  
  ; Predicates
  (:predicates
    (at ?agent - agent ?location - location)
    (on-ground ?object - object ?location - location)
    (sleeping ?monster - monster)
    (carrying ?agent - agent ?object - object)
    (defeated ?monster - monster)
  )
  
  ; Actions
  (:action move
    :parameters (?a - agent ?o - object ?l1 - location ?l2 - location)
    :preconditions (and
      (at ?a ?l1)
      (on-ground ?o ?l1)
    )
    :effects (and
      (not (at ?a ?l1))
      (at ?a ?l2)
    )
  )
  
  (:action pick-up
    :parameters (?a - agent ?o - object ?l - location)
    :preconditions (and
      (at ?a ?l)
      (on-ground ?o ?l)
    )
    :effects (and
      (not (on-ground ?o ?l))
      (carrying ?a ?o)
    )
  )
  
  (:action defeat
    :parameters (?a - agent ?m - monster ?l - location)
    :preconditions (and
      (at ?a ?l)
      (carrying ?a ?o)
      (sleeping ?m)
    )
    :effects (and
      (not (sleeping ?m))
      (defeated ?m)
    )
  )
)