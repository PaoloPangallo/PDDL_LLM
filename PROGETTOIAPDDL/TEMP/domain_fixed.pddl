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
  (:action go_to
    :parameters (?x - location ?y - location ?z - hero)
    :precondition (and (at ?z ?x) (not (at ?z ?y)))
    :effect (and (at ?z ?y) (not (at ?z ?x))))
  (:action use-sword
    :parameters (?x - location ?y - hero ?z - object)
    :precondition (and (at ?y ?x) (carrying ?y ?z))
    :effect (and (not (sleeping ?z ?x)) (not (carrying ?y ?z)))))


(define (domain example-domain)
  (:requirements :strips :typing)
  (:types agent object location monster sleeping defeated)
  (:predicates
    (at ?x - agent ?y - location)
    (on_ground ?x - object ?y - location)
    (carrying ?x - agent ?y - object)
    (sleeping ?x - monster)
    (defeated ?x - monster))
  (:action move
    :parameters (?h - agent ?from - location ?to - location)
    :precondition (and (at ?h ?from))
    :effect (and (not (at ?h ?from)) (at ?h ?to)))
  (:action pickup
    :parameters (?h - agent ?s - object ?l - location)
    :precondition (and (at ?h ?l) (on_ground ?s ?l))
    :effect (and (carrying ?h ?s) (not (on_ground ?s ?l))))
  (:action defeat
    :parameters (?h - agent ?d - monster ?l - location)
    :precondition (and (at ?h ?l) (carrying ?h sword_of_fire) (sleeping ?d))
    :effect (and (defeated ?d) (not (sleeping ?d))))
)