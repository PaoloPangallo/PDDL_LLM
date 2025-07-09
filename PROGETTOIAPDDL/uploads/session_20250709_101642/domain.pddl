(define (domain my-domain)
  (:requirements :strips :typing)
  (:types agent location monster object)
  (:predicates
    (at ?h - agent ?l - location)
    (on_ground ?sword_of_fire - object ?l - location)
    (sleeping ?d - monster)
    (defeated ?d - monster)
  )

  (:action move
    :parameters (?h - agent ?from - location ?to - location)
    :precondition (and (at ?h ?from))
    :effect       (and (not (at ?h ?from)) (at ?h ?to))
  )

  (:action carry-and-move
    :parameters (?h - agent ?o - object ?from - location ?to - location)
    :precondition (and (at ?h ?from) (on_ground ?o ?from))
    :effect       (and (not (at ?h ?from)) (at ?h ?to) (not (on_ground ?o ?from)) (on_ground ?o ?to))
  )

  (:action defeat
    :parameters (?h - agent ?d - monster ?l - location ?sword_of_fire - object)
    :precondition (and (at ?h ?l) (on_ground ?sword_of_fire ?l) (sleeping ?d))
    :effect       (and (defeated ?d) (not (sleeping ?d)))
  )
)