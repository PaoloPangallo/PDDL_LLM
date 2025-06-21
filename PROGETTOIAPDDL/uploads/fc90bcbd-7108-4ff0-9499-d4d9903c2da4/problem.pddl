(define (domain varnak-adventure)
  (:requirements :strips)
  (:types agent location object monster)

  (:predicates
    (at ?a - agent ?l - location)
    (has ?a - agent ?o - object)
    (on-ground ?o - object ?l - location)
    (sleeping ?m - monster)
    (awake ?m - monster)
    (defeated ?m - monster)
  )

  (:action move
    :parameters (?a - agent ?l1 - location ?l2 - location)
    :precondition (and (at ?a ?l1))
    :effect (and (not (at ?a ?l1)) (at ?a ?l2))
  )

  (:action pickup
    :parameters (?a - agent ?o - object ?l - location)
    :precondition (and (at ?a ?l) (on-ground ?o ?l))
    :effect (and (not (on-ground ?o ?l)) (has ?a ?o))
  )

  (:action putdown
    :parameters (?a - agent ?o - object ?l - location)
    :precondition (has ?a ?o)
    :effect (and (not (has ?a ?o)) (on-ground ?o ?l))
  )

  (:action wake-up
    :parameters (?m - monster)
    :precondition (sleeping ?m)
    :effect (and (not (sleeping ?m)) (awake ?m))
  )

  (:action slay
    :parameters (?a - agent ?m - monster)
    :precondition (and (at ?a cave) (has ?a sword) (awake ?m))
    :effect (defeated ?m)
  )
)
