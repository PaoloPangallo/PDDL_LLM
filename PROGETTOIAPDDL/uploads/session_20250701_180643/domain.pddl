(define (domain puzzle)
  (:requirements :strips :typing)
  (:types
    box - object
    key - object
    door - object
    room - location
    sword - object
    dragon - object
    village - location
    tower - location
  )
  (:predicates
    (at ?x - object ?y - location)
    (on ?x - object ?y - location)
    (sleeping ?x - object)
    (on-ground ?x - object ?y - location)
  )
  (:action move-box
    :parameters (?x - object ?y - location)
    :precondition (and (at ?x ?z - location) (not (at ?x ?y)))
    :effect (and (at ?x ?y) (not (at ?x ?z)))
  )
  (:action move-key
    :parameters (?x - object ?y - location)
    :precondition (and (at ?x ?z - location) (not (at ?x ?y)))
    :effect (and (at ?x ?y) (not (at ?x ?z)))
  )
  (:action move-door
    :parameters (?x - object ?y - location)
    :precondition (and (at ?x ?z - location) (not (at ?x ?y)))
    :effect (and (at ?x ?y) (not (at ?x ?z)))
  )
  (:action open-door
    :parameters (?x - object ?y - object)
    :precondition (and (at ?x ?z - location) (at ?y ?z - location) (on ?x ?z) (on ?y ?z))
    :effect (and (at ?x ?z - location) (at ?y ?z - location) (on ?x ?z) (on ?y ?z) (on ?x ?y))
  )
  (:action move-sword
    :parameters (?x - object ?y - location)
    :precondition (and (at ?x ?z - location) (not (at ?x ?y)))
    :effect (and (at ?x ?y) (not (at ?x ?z)))
  )
  (:action move-dragon
    :parameters (?x - object ?y - location)
    :precondition (and (at ?x ?z - location) (not (at ?x ?y)))
    :effect (and (at ?x ?y) (not (at ?x ?z)))
  )
  (:action wake-dragon
    :parameters (?x - object)
    :precondition (at ?x ?y - location)
    :effect (and (at ?x ?y - location) (not (sleeping ?x)))
  )
)