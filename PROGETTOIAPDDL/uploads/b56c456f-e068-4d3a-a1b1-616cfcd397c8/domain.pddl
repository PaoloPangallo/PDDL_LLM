(define (domain la-spada-di-varnak))
  (:requirements :strips)
  (:types hero location sword monster)
  (:predicates
    (at ?h - hero ?l - location)
    (has-sword ?h - hero)
    (hidden ?s - sword ?l - location)
    (asleep ?m - monster)
    (defeated ?m - monster)
  )

  (:action move
    :parameters (?h - hero ?from - location ?to - location)
    :precondition (at ?h ?from)
    :effect (and (not (at ?h ?from)) (at ?h ?to))
  )

  (:action find-sword
    :parameters (?h - hero ?l - location)
    :precondition (and (at ?h ?l) (hidden sword ?l))
    :effect (and (not (hidden sword ?l)) (has-sword ?h)))

  (:action wake-monster
    :parameters (?h - hero ?m - monster)
    :precondition (and (at ?h ?l) (asleep ?m))
    :effect (and (not (asleep ?m)) (awake ?m))
  )

  (:action defeat-monster
    :parameters (?h - hero ?m - monster)
    :precondition (and (at ?h ?l) (awake ?m) (has-sword ?h))
    :effect (defeated ?m)
  )