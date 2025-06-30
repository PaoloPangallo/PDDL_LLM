(define (domain world-quest)
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

    (:action pick-up
      :parameters (?h - hero ?o - object ?l - location)
      :precondition (and (at ?h ?l) (on-ground ?o))
      :effect (has-object ?h ?o)
    )

    (:action put-down
      :parameters (?h - hero ?o - object ?l - location)
      :precondition (and (has-object ?h ?o))
      :effect (and (not (has-object ?h ?o)) (on-ground ?o))
    )

    (:action slay-dragon
      :parameters (?h - hero ?d - dragon)
      :precondition (and (at ?h tower-of-varnak) (has-object ?h sword-of-fire) (alive ?d))
      :effect (and (not (alive ?d)) (defeated ?d))
    )
  )