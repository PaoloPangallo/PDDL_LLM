(define (domain world-exploration)
    (:requirements :strips)
    (:types agent location item)
    (:predicates
      (at ?a - agent ?l - location)
      (has-item ?a - agent ?i - item)
      (open ?l - location)
      (contains ?l - location ?i - item)
    )

    (:action move
      :parameters (?a - agent ?from - location ?to - location)
      :precondition (and (at ?a ?from) (open ?to))
      :effect (and (not (at ?a ?from)) (at ?a ?to))
    )

    (:action take
      :parameters (?a - agent ?l - location ?i - item)
      :precondition (and (at ?a ?l) (contains ?l ?i))
      :effect (and (has-item ?a ?i) (not (contains ?l ?i)))
    )
  )