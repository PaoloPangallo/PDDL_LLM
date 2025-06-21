(define (domain travel-world))
  (:requirements :strips)
  (:types location agent)
  (:predicates
    (at ?a - agent ?l - location)
    (on-water ?l - location)
  )

  (:action move
    :parameters (?a - agent ?from - location ?to - location)
    :precondition (and (at ?a ?from) (on-path ?from ?to))
    :effect (and (not (at ?a ?from)) (at ?a ?to)))

  (:action swim
    :parameters (?a - agent ?l - location)
    :precondition (and (at ?a ?l) (on-water ?l))
    :effect (at ?a (find-neighboring-land ?l))))

  (:action find-neighboring-land
    :parameters (?l - location)
    :precondition (on-water ?l)
    :effect (exists (?neighbor) (and (on-path ?neighbor ?l) (at ?neighbor (find-neighboring-land ?neighbor))))))