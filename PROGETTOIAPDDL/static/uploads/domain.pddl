(define (domain quest-domain)
  (:types agent object location monster)

  (:predicates
    ; Agent predicates
    (at ?a - agent ?l - location)
    (carrying ?a - agent ?o - object)
    ; Object predicates
    (on-ground ?o - object ?l - location)
    ; Monster predicates
    (sleeping ?m - monster)
    (defeated ?m - monster)
  )

  (:action move-agent
    :parameters (?a - agent ?from - location ?to - location)
    :precondition (and (at ?a ?from))
    :effect (and (not (at ?a ?from)) (at ?a ?to))
  )

  (:action pick-object
    :parameters (?a - agent ?o - object ?l - location)
    :precondition (and (at ?a ?l) (on-ground ?o ?l))
    :effect (and (not (on-ground ?o ?l)) (carrying ?a ?o))
  )

  (:action drop-object
    :parameters (?a - agent ?o - object ?l - location)
    :precondition (and (at ?a ?l) (carrying ?a ?o))
    :effect (and (not (carrying ?a ?o)) (on-ground ?o ?l))
  )

  (:action defeat-monster
    :parameters (?a - agent ?m - monster ?o - object)
    :precondition (and (at ?a ?l) (carrying ?a ?o) (sleeping ?m))
    :effect (defeated ?m)
  )
)