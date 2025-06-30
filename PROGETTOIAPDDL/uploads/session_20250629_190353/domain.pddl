(define (domain ice-adventure)
    (:requirements :strips)
    (:types hero location monster sword)
    (:predicates
      (at ?h - hero ?l - location)
      (has-sword ?h - hero)
      (alive ?m - monster)
      (in ?m - monster ?l - location)
      (frozen ?m - monster)
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

    (:action defeat
      :parameters (?h - hero ?m - monster ?l - location)
      :precondition (and (at ?h ?l) (in ?m ?l) (has-sword ?h) (alive ?m))
      :effect (and (not (alive ?m)) (not (frozen ?m)))
    )
  )