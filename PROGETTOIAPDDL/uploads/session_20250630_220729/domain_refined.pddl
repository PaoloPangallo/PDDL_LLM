(define (domain robot_quest)
  (:requirements :strips :typing)
  (:types
    location
    robot
    battery
    object
  )
  (:predicates
    (at ?robot ?location)
    (has_battery ?robot ?battery)
    (holds ?robot ?object)
    (in ?object ?location)
  )
  (:action move
    :parameters (?robot ?from ?to)
    :precondition (and (at ?robot ?from) (has_battery ?robot ?battery))
    :effect (and (not (at ?robot ?from)) (at ?robot ?to))
  )
  (:action pick
    :parameters (?robot ?object)
    :precondition (and (at ?robot ?location) (in ?object ?location))
    :effect (and (holds ?robot ?object) (not (in ?object ?location)))
  )
  (:action drop
    :parameters (?robot ?object)
    :precondition (and (at ?robot ?location) (holds ?robot ?object))
    :effect (and (not (holds ?robot ?object)) (in ?object ?location))
  )
)