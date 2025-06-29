(define (domain my_domain)
    (:requirements :strips)
    (:types agent object location)
    (:predicates
      (at ?a - agent ?l - location)
      (holding ?a - agent ?o - object)
      (on ?o - object ?l - location)
      (clear ?l - location)
      (block ?b1 - object ?b2 - object)
    )

    (:action pickup
      :parameters (?a - agent ?o - object)
      :precondition (and (at ?a ?l) (on ?o ?l) (clear ?l))
      :effect (and (not (on ?o ?l)) (holding ?a ?o))
    )

    (:action putdown
      :parameters (?a - agent ?o - object)
      :precondition (holding ?a ?o)
      :effect (and (clear (location ?o)) (not (holding ?a ?o)) (on ?o (location ?a)))
    )

    (:action move-to
      :parameters (?a - agent ?l1 - location ?l2 - location)
      :precondition (and (at ?a ?l1) (clear ?l2))
      :effect (and (not (at ?a ?l1)) (at ?a ?l2))
    )

    (:action stack
      :parameters (?a - agent ?o1 - object ?o2 - object)
      :precondition (and (clear (location ?a)) (holding ?a ?o1) (on ?o2 (location ?a)))
      :effect (and (not (holding ?a ?o1)) (block ?o1 ?o2) (clear (location ?o1)) (on ?o1 ?a))
    )

    (:action unstack
      :parameters (?a - agent ?o1 - object)
      :precondition (and (holding ?a ?o1) (block ?o1 ?o2))
      :effect (and (clear (location ?o1)) (not (block ?o1 ?o2)) (on ?o1 (location ?a)))
    )
  )