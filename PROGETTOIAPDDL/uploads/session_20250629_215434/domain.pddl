(define (domain quest-of-fire)
    (:requirements :strips)
    (:types hero location dragon sword)
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
      :parameters (?h - hero ?o - object ?l - location)
      :precondition (and (at ?h ?l) (on-ground ?o))
      :effect (and (has-object ?h ?o) (not (on-ground ?o)))
    )

    (:action slay-dragon
      :parameters (?h - hero ?d - dragon ?l - location)
      :precondition (and (at ?h ?l) (in ?d ?l) (has-object ?h sword-of-fire) (alive ?d))
      :effect (and (not (alive ?d)) (defeated ?d))
    )
  )