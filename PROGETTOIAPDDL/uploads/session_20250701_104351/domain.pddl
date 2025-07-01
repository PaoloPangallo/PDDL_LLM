(define (domain delivery)
  (:requirements :strips :typing)
  (:types
    location
    truck
    package
  )
  (:predicates
    (at ?truck ?location)
    (has_package ?truck ?package)
    (in ?package ?location)
  )
  (:action move
    :parameters (?truck ?from ?to)
    :precondition (and (at ?truck ?from) (has_package ?truck ?package))
    :effect (and (not (at ?truck ?from)) (at ?truck ?to))
  )
  (:action pick
    :parameters (?truck ?package)
    :precondition (and (at ?truck ?location) (in ?package ?location))
    :effect (and (has_package ?truck ?package) (not (in ?package ?location)))
  )
  (:action drop
    :parameters (?truck ?package)
    :precondition (and (at ?truck ?location) (has_package ?truck ?package))
    :effect (and (not (has_package ?truck ?package)) (in ?package ?location))
  )
)