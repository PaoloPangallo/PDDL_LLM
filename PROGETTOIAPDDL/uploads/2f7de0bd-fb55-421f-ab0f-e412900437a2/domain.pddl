(define (domain la-spada-di-varnak))
  (:requirements :strips)
  (:types hero location sword monster)
  (:predicates
    (at ?h - hero ?l - location)
    (has-sword ?h - hero)
    (hidden ?s - sword ?l - location)
    (sleeping ?m - monster)
    (defeated ?m - monster)
  )

  (:action move
    :parameters (?h - hero ?from - location ?to - location)
    :precondition (and (at ?h ?from))
    :effect (and (not (at ?h ?from)) (at ?h ?to)))

  (:action take-sword
    :parameters (?h - hero ?l - location)
    :precondition (and (at ?h ?l) (hidden sword ?l))
    :effect (and (not (hidden sword ?l)) (has-sword ?h)))

  (:action wake-dragon
    :parameters (?h - hero ?m - monster)
    :precondition (and (at ?h cave) (sleeping ?m))
    :effect (not (sleeping ?m)))

  (:action defeat-dragon
    :parameters (?h - hero ?m - monster)
    :precondition (and (at ?h cave) (defeated ?m) (has-sword ?h))
    :effect (not (sleeping ?m) (defeated ?m)))