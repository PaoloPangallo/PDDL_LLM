(define (domain quest-fantasy)
    (:requirements :strips)
    (:types hero location dragon weapon)
    (:predicates
      (at ?h - hero ?l - location)
      (has-weapon ?h - hero ?w - weapon)
      (alive ?d - dragon)
      (in ?d - dragon ?l - location)
      (defeated ?d - dragon)
    )

    (:action move
      :parameters (?h - hero ?from - location ?to - location)
      :precondition (at ?h ?from)
      :effect (and (not (at ?h ?from)) (at ?h ?to))
    )

    (:action take-weapon
      :parameters (?h - hero ?l - location ?w - weapon)
      :precondition (and (at ?h ?l))
      :effect (has-weapon ?h ?w)
    )

    (:action fight
      :parameters (?h - hero ?d - dragon ?l - location)
      :precondition (and (at ?h ?l) (in ?d ?l) (has-weapon ?h sword-of-fire))
      :effect (and (defeated ?d) (not (alive ?d))))
  )