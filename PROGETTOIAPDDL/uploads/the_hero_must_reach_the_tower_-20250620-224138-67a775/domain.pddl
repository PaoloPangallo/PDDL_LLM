(define (domain dragon-quest)
    (:requirements :strips)
    (:types hero location dragon sword)
    (:predicates
      (at ?h - hero ?l - location)
      (has-sword ?h - hero)
      (alive ?d - dragon)
      (in ?d - dragon ?l - location)
    )

    (:action move
      :parameters (?h - hero ?from - location ?to - location)
      :precondition (at ?h ?from)
      :effect (and (not (at ?h ?from)) (at ?h ?to))
    )

    (:action take-sword
      :parameters (?h - hero ?l - location)
      :precondition (and (at ?h ?l))
      :effect (has-sword ?h)
    )

    (:action slay-dragon
      :parameters (?h - hero ?d - dragon ?l - location)
      :precondition (and (at ?h ?l) (in ?d ?l) (has-sword ?h) (alive ?d))
      :effect (not (alive ?d))
    )
  )