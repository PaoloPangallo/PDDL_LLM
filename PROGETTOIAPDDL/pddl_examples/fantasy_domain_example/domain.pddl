(define (domain fantasy-domain)
  (:requirements :strips :typing)
  (:types hero location object monster)
  (:predicates
    (at ?h - hero ?l - location)
    (has ?h - hero ?o - object)
    (alive ?m - monster)
  )
  (:action move
    :parameters (?h - hero ?from - location ?to - location)
    :precondition (at ?h ?from)
    :effect (and (not (at ?h ?from)) (at ?h ?to))
  )
  (:action pick-up
    :parameters (?h - hero ?o - object ?l - location)
    :precondition (and (at ?h ?l))
    :effect (has ?h ?o)
  )
  (:action defeat
    :parameters (?h - hero ?m - monster)
    :precondition (and (has ?h sword-of-fire) (alive ?m))
    :effect (not (alive ?m))
  )
)