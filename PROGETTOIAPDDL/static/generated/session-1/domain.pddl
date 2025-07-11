(define (domain quest)

  ; Types
  (:types 
    agent - Type
    location - Type
    object - Type
    monster - Type
  )

  ; Predicates
  (:predicates 
    (at ?a ?l) - (agent location)
    (on-ground ?o ?l) - (object location)
    (sleeping ?m) - (monster)
    (carrying ?a ?o) - (agent object)
    (defeated ?m) - (monster)
  )

  ; Actions
  (:action 
    travel-to-location
    :parameters (?a ?l1 ?l2)
    :precondition (and (at ?a ?l1))
    :effect (and (not (at ?a ?l1)) (at ?a ?l2))
  )

  (:action 
    pick-up-object
    :parameters (?a ?o ?l)
    :precondition (and (on-ground ?o ?l) (at ?a ?l))
    :effect (and (carrying ?a ?o) (not (on-ground ?o ?l)))
  )

  (:action 
    approach-monster
    :parameters (?a ?m ?l)
    :precondition (and (at ?a ?l) (sleeping ?m))
    :effect (and (not (sleeping ?m)) (carrying ?a ?sword_of_fire) (at ?a ?l))
  )

  (:action 
    defeat-monster
    :parameters (?a ?m)
    :precondition (and (carrying ?a ?sword_of_fire) (at ?a ?l) (on-ground ?ice_dragon ?l))
    :effect (and (defeated ?m) (not (carrying ?a ?sword_of_fire)) (not (sleeping ?m)))
  )

)