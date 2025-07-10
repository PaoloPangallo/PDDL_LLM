(define (domain hero-adventure)
  (:types 
    ; Define the types of objects in the world
    location - location
    agent - agent
    object - object
    monster - monster)

  (:predicates 
    ; Declare predicates for actions and fluents
    (at ?a ?l) - (agent ?a location ?l)
    (on-ground ?o ?l) - (object ?o location ?l)
    (sleeping ?m) - (monster ?m)
    (carrying ?a ?o) - (agent ?a object ?o)
    (defeated ?m) - (monster ?m))

  (:action 
    ; Declare actions
    move
      :parameters (?a ?from ?to)
      :preconditions 
        (and (at ?a ?from) (not (at ?a ?to)))
      :effects 
        (and (at ?a ?to) (not (at ?a ?from))))
  )