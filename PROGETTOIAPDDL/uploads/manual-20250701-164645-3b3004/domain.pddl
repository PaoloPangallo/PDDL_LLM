(define (domain charging-station)
  (:requirements :strips :typing)
  (:types 
    location 
    object 
    entity 
    robot 
    charging-station 
    battery 
    obstacle)
  (:predicates 
    (at ?x - location) 
    (on-ground ?x - object) 
    (sleeping ?x - entity) 
    (carrying ?x - robot ?y - object))
  (:action move
    :parameters (?x - location ?y - location ?z - robot)
    :precondition (and (at ?z ?x) (not (at ?z ?y)))
    :effect (and (at ?z ?y) (not (at ?z ?x))))
  (:action pick-up
    :parameters (?x - location ?y - object ?z - robot)
    :precondition (and (at ?z ?x) (on-ground ?y ?x) (not (carrying ?z ?y)))
    :effect (and (carrying ?z ?y) (not (on-ground ?y ?x))))
  (:action drop
    :parameters (?x - location ?y - object ?z - robot)
    :precondition (and (at ?z ?x) (carrying ?z ?y))
    :effect (and (not (carrying ?z ?y)) (on-ground ?y ?x)))
  (:action recharge
    :parameters (?x - location ?y - robot)
    :precondition (and (at ?y ?x) (on-ground battery ?x))
    :effect (and (not (sleeping ?y ?x)) (not (carrying ?y battery))))
  (:action go-to
    :parameters (?x - location ?y - location ?z - robot)
    :precondition (and (at ?z ?x) (not (at ?z ?y)))
    :effect (and (at ?z ?y) (not (at ?z ?x))))
  (:action navigate-around-obstacle
    :parameters (?x - location ?y - location ?z - robot)
    :precondition (and (at ?z ?x) (on-ground obstacle ?y))
    :effect (and (at ?z ?y) (not (on-ground obstacle ?y)))))