(define (domain robot-reach-charging-station)
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
    :effect (and (at ?z ?y) (not (on-ground obstacle ?y))))
  (:action block-obstacle
    :parameters (?x - location ?y - location ?z - robot)
    :precondition (and (at ?z ?x) (on-ground obstacle ?y))
    :effect (and (at ?z ?y) (on-ground obstacle ?y)))
  (:action unblock-obstacle
    :parameters (?x - location ?y - location ?z - robot)
    :precondition (and (at ?z ?x) (on-ground obstacle ?y))
    :effect (and (not (on-ground obstacle ?y))))
  (:action charging-station-battery
    :parameters (?x - location ?y - robot)
    :precondition (and (at ?y ?x) (on-ground battery ?x))
    :effect (and (not (sleeping ?y ?x)) (not (carrying ?y battery)))))