(define (domain pc-assembly)
  (:requirements :strips :typing)
  (:types agent component location)
  (:predicates
    (at        ?r - agent ?l - location)
    (has       ?r - agent ?c - component)
    (mounted   ?c - component)
  )
  (:action fetch-part
    :parameters (?r - agent ?c - component ?l - location)
    :precondition (and (at ?r ?l) (not (has ?r ?c)))
    :effect       (and (has ?r ?c))
  )
  (:action move
    :parameters (?r - agent ?from - location ?to - location)
    :precondition (at ?r ?from)
    :effect       (and (not (at ?r ?from)) (at ?r ?to))
  )
  (:action mount
    :parameters (?r - agent ?c - component ?w - location)
    :precondition (and (at ?r ?w) (has ?r ?c))
    :effect       (and (mounted ?c) (not (has ?r ?c)))
  )
)
