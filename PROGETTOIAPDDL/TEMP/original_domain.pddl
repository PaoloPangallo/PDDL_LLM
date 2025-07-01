(define (domain world)
  (:requirements :strips :typing)
  (:types 
    location 
    object 
    entity 
    sword 
    dragon 
    ground 
    tower 
    hero 
    ice 
    fire)
  (:predicates 
    (at ?x - location) 
    (on-ground ?x - object) 
    (sleeping ?x - entity) 
    (carrying ?x - hero ?y - object))
  (:action move
    :parameters (?x - location ?y - location ?z - hero)
    :precondition (and (at ?z ?x) (not (at ?z ?y)))
    :effect (and (at ?z ?y) (not (at ?z ?x))))
  (:action pick-up
    :parameters (?x - location ?y - object ?z - hero)
    :precondition (and (at ?z ?x) (on-ground ?y ?x) (not (carrying ?z ?y)))
    :effect (and (carrying ?z ?y) (not (on-ground ?y ?x))))
  (:action drop
    :parameters (?x - location ?y - object ?z - hero)
    :precondition (and (at ?z ?x) (carrying ?z ?y))
    :effect (and (not (carrying ?z ?y)) (on-ground ?y ?x)))
  (:action fight
    :parameters (?x - location ?y - entity ?z - hero)
    :precondition (and (at ?z ?x) (sleeping ?y ?x))
    :effect (and (not (sleeping ?y ?x)) (not (carrying ?z ?y))))
  (:action go-to
    :parameters (?x - location ?y - location ?z - hero)
    :precondition (and (at ?z ?x) (not (at ?z ?y)))
    :effect (and (at ?z ?y) (not (at ?z ?x))))
  (:action use-sword
    :parameters (?x - location ?y - hero ?z - object)
    :precondition (and (at ?y ?x) (carrying ?y ?z))
    :effect (and (not (sleeping ?z ?x)) (not (carrying ?y ?z)))))