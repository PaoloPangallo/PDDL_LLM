(define (domain world-context)
  (:requirements :strips :typing)
  (:types
    village - location
    sword - object
    tower - location
    dragon - object
  )
  (:predicates
    (at ?x - location)
    (on-ground ?x - object ?y - location)
    (sleeping ?x - object)
  )
  (:action move
    :parameters (?x - location ?y - location)
    :precondition (and (at ?x ?y))
    :effect (and (not (at ?x ?y)) (at ?x ?y))
  )
  (:action take
    :parameters (?x - location ?y - object)
    :precondition (and (at ?x ?y) (on-ground ?y ?x))
    :effect (and (at ?x ?y) (on-ground ?y ?x) (on ?x ?y))
  )
  (:action use
    :parameters (?x - object ?y - object)
    :precondition (and (at ?x ?y) (on ?x ?y))
    :effect (and (at ?x ?y) (on ?x ?y) (sleeping ?y))
  )
)