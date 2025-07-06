(define (domain robot-domain)
  (:requirements :strips :typing)
  (:types
    robot - object
    charging-station - object
    obstacle - object
    battery - object
    ground - object
  )
  (:predicates
    (at ?x - object ?y - object)
    (on-ground ?x - object ?y - object)
    (blocked ?x - object ?y - object)
  )
  (:action move
    :parameters (?x - object ?y - object)
    :precondition (and (at ?x ?y) (on-ground ?x ?y))
    :effect (and (not (at ?x ?y)) (at ?x ?z) (on-ground ?x ?z))
  )
  (:action recharge
    :parameters (?x - object ?y - object)
    :precondition (and (at ?x ?y) (on-ground ?x ?y) (blocked ?x ?y))
    :effect (and (not (blocked ?x ?y)) (on-ground ?x ?y))
  )
)