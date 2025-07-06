(define (domain tower-of-varnak)
  (:requirements :strips :typing)
  (:types
    :object
    :location
    :weapon
    :dragon
    :state
  )
  (:predicates
    (at ?x - :location)
    (on-ground ?x - :object)
    (carrying ?x - :object ?y - :object)
    (defeated ?x - :dragon)
  )
  (:action move
    :parameters (?x - :object ?y - :location)
    :precondition (and (at ?x ?y) (on-ground ?x))
    :effect (not (at ?x ?y)) (at ?x ?y))
  (:action pick-up
    :parameters (?x - :object ?y - :object)
    :precondition (and (at ?x ?y) (on-ground ?x))
    :effect (carrying ?x ?y))
  (:action drop
    :parameters (?x - :object ?y - :object)
    :precondition (and (at ?x ?y) (carrying ?x ?y))
    :effect (not (carrying ?x ?y)))
  (:action fight
    :parameters (?x - :object ?y - :dragon)
    :precondition (and (at ?x ?y) (carrying ?x ?y))
    :effect (defeated ?y)))