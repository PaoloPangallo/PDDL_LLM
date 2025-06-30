(define (domain world-conquest)
    (:requirements :strips)
    (:types hero location dragon object)
    (:predicates
      (at ?h - hero ?l - location)
      (has-object ?h - hero ?o - object)
      (alive ?d - dragon)
      (in ?d - dragon ?l - location)
      (defeated ?d - dragon)
    )

    (:action move
      :parameters (?h - hero ?from - location ?to - location)
      :precondition (at ?h ?from)
      :effect (and (not (at ?h ?from)) (at ?h ?to))
    )

    (:action take-object
      :parameters (?h - hero ?l - location ?o - object)
      :precondition (and (at ?h ?l))
      :effect (has-object ?h ?o)
    )

    (:action fight-dragon
      :parameters (?h - hero ?d - dragon ?l - location)
      :precondition (and (at ?h ?l) (in ?d ?l) (has-object ?h sword-of-fire))
      :effect (and (defeated ?d) (not (alive ?d)))
    )
  )