(define (domain simple-world)
    (:requirements :strips)
    (:types location object agent)
    (:predicates
      (at ?a - agent ?l - location)
      (on ?o - object ?l - location)
      (clear ?l - location)
    )

    (:action move
      :parameters (?a - agent ?from - location ?to - location)
      :precondition (and (at ?a ?from) (clear ?from))
      :effect (and (not (at ?a ?from)) (at ?a ?to) (clear ?from))
    )

    (:action pickup
      :parameters (?a - agent ?o - object ?l - location)
      :precondition (and (at ?a ?l) (on ?o ?l))
      :effect (and (not (on ?o ?l)) (holding ?o ?a))
    )

    (:action putdown
      :parameters (?a - agent ?o - object ?l - location)
      :precondition (and (at ?a ?l) (holding ?o ?a))
      :effect (and (not (holding ?o ?a)) (on ?o ?l))
    )
  )

  (:action take-from-clear
    :parameters (?a - agent ?o - object ?to - location)
    :precondition (and (at ?a ?to) (clear ?to) (holding ?o ?a))
    :effect (and (not (holding ?o ?a)) (clear ?from) (on ?o ?from))
  )

  (:action put-on-clear
    :parameters (?a - agent ?o - object ?to - location)
    :precondition (and (at ?a ?to) (clear ?to) (holding ?o ?a))
    :effect (and (not (holding ?o ?a)) (clear ?from) (on ?o ?from))
  )