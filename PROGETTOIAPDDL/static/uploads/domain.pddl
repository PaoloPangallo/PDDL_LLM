(define (domain hero-quest)
  (:requirements :strips)
  
  ; Predicates
  (:predicates
    (at ?a - agent ?l - location)
    (on-ground ?o - object ?l - location)
    (sleeping ?m - monster)
    (defeated ?m - monster)
  )
  
  ; Types
  (:types
    agent location monster object
  )
  
  ; Actions
  (:action move
    :parameters (?a - agent ?l1 - location ?l2 - location)
    :precondition (and (at ?a ?l1) (not (= ?l1 ?l2)))
    :effect (and (at ?a ?l2) (not (at ?a ?l1)))
  )
  
  (:action pick-up
    :parameters (?a - agent ?o - object ?l - location)
    :precondition (and (at ?a ?l) (on-ground ?o ?l))
    :effect (and (at ?a ?l) (not (on-ground ?o ?l)))
  )
  
  (:action defeat
    :parameters (?a - agent ?m - monster)
    :precondition (and (at ?a ?l) (sleeping ?m))
    :effect (and (defeated ?m))
  )
)