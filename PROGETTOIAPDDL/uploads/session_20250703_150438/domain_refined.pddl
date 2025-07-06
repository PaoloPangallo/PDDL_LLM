(define (domain world-context)
  (:requirements :strips :typing)
  (:types 
    village - location 
    tower - location 
    sword - object 
    dragon - object 
    hero - agent 
    ground - location 
  )
  (:predicates 
    (at ?a ?l) 
    (on-ground ?o ?l) 
    (sleeping ?o) 
    (carrying ?a ?o) 
    (defeated ?o) 
  )
  (:action move 
    :parameters (?a ?l)
    :precondition (and (at ?a ?l1) (not (at ?a ?l)))
    :effect (and (at ?a ?l) (not (at ?a ?l1)))
  )
  (:action pick-up 
    :parameters (?a ?o ?l)
    :precondition (and (at ?a ?l) (on-ground ?o ?l))
    :effect (and (at ?a ?l) (carrying ?a ?o) (not (on-ground ?o ?l)))
  )
  (:action put-down 
    :parameters (?a ?o ?l)
    :precondition (and (at ?a ?l) (carrying ?a ?o))
    :effect (and (at ?a ?l) (not (carrying ?a ?o)) (on-ground ?o ?l))
  )
  (:action defeat 
    :parameters (?a ?o)
    :precondition (and (at ?a ?l) (carrying ?a ?o) (at ?o ?l))
    :effect (and (at ?a ?l) (defeated ?o) (not (carrying ?a ?o)))
  )
)