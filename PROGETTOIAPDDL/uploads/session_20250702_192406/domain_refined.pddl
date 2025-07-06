(define (domain hero-adventure)
  (:requirements :strips :typing)
  (:types
    location - location
    object - object
    condition - condition
  )
  (:predicates
    (at ?a - location)
    (on-ground ?a - object)
    (sleeping ?a - object)
    (defeated ?a - object)
    (carrying ?a - object)
  )
  (:action move
    :parameters (?a - location ?b - location)
    :precondition (and (at ?a ?b))
    :effect (and (not (at ?a ?b)) (at ?a ?b))
  )
  (:action pick-up
    :parameters (?a - object ?b - object)
    :precondition (and (on-ground ?a ?b) (at ?a ?b))
    :effect (and (carrying ?a ?b) (not (on-ground ?a ?b)))
  )
  (:action use-sword
    :parameters (?a - object)
    :precondition (and (at ?a ?a) (carrying ?a ?b))
    :effect (and (not (sleeping ?b)) (defeated ?b))
  )
)