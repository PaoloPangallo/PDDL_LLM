(define (domain la_spada_di_varnak))
  (:requirements :strips)
  (:types hero location sword monster)
  (:predicates
    (at ?h - hero ?l - location)
    (has-item ?h - hero ?i - item)
    (hidden ?i - item ?l - location)
    (asleep ?m - monster)
    (defeated ?m - monster)
  )

  (:action move
    :parameters (?h - hero ?from - location ?to - location)
    :precondition (and (at ?h ?from))
    :effect (and (not (at ?h ?from)) (at ?h ?to)))

  (:action take-item
    :parameters (?h - hero ?i - item ?l - location)
    :precondition (and (at ?h ?l) (hidden ?i ?l))
    :effect (and (not (hidden ?i ?l)) (has-item ?h ?i)))

  (:action wake-monster
    :parameters (?m - monster)
    :precondition (asleep ?m)
    :effect (not (asleep ?m)))

  (:action defeat-monster
    :parameters (?h - hero ?m - monster)
    :precondition (and (at ?h ?l) (asleep ?m))
    :effect (and (defeated ?m) (not (asleep ?m))))