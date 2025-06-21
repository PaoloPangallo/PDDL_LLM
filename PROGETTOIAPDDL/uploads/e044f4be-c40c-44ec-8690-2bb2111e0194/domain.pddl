(define (domain la-spada-di-varnak))
  (:requirements :strips)
  (:types hero location sword monster)
  (:predicates
    (at ?h - hero ?l - location)
    (has-sword ?h - hero)
    (hidden ?o - object ?l - location)
    (asleep ?m - monster)
    (defeated ?m - monster)
  )

  (:action move
    :parameters (?h - hero ?from - location ?to - location)
    :precondition (at ?h ?from)
    :effect (and (not (at ?h ?from)) (at ?h ?to))
  )

  (:action take-sword
    :parameters (?h - hero ?l - location)
    :precondition (and (at ?h ?l) (hidden sword ?l))
    :effect (has-sword ?h)
  )

  (:action wake-dragon
    :parameters (?h - hero)
    :precondition (at ?h cave)
    :effect (not (asleep dragon))
  )

  (:action defeat-dragon
    :parameters (?h - hero)
    :precondition (and (has-sword ?h) (not (defeated dragon)))
    :effect (defeated dragon)
  )