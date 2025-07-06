(define (domain hero)
  (:requirements :strips :typing)
  (:types
    village - location
    tower - location
    sword - object
    dragon - object
    hero - object
  )
  (:predicates
    (at ?x - location)
    (on-ground ?x - object ?y - location)
    (sleeping ?x - object)
    (carrying ?x - object ?y - object)
    (defeated ?x - object)
  )
  (:action move-hero
    :parameters (?x - location)
    :precondition (and (at hero ?x))
    :effect (not (at hero ?x))
  )
  (:action pick-sword
    :parameters (?x - location)
    :precondition (and (at hero ?x) (on-ground sword-of-fire ?x))
    :effect (and (carrying hero sword-of-fire) (not (on-ground sword-of-fire ?x)))
  )
  (:action move-sword
    :parameters (?x - location)
    :precondition (and (at hero ?x) (carrying hero sword-of-fire))
    :effect (not (at hero ?x))
  )
  (:action attack-dragon
    :parameters (?x - object)
    :precondition (and (at hero ?x) (carrying hero sword-of-fire) (sleeping ice-dragon))
    :effect (and (defeated ice-dragon) (not (sleeping ice-dragon)))
  )
)