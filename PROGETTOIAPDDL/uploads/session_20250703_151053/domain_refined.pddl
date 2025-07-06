(define (domain robot-charging)
  (:requirements :strips :typing)
  (:types
    robot - robot
    charging-station - charging-station
    obstacle - obstacle
    battery - battery
    location - location
  )
  (:predicates
    (at ?r - robot ?l - location)
    (on-ground ?b - battery ?l - location)
    (blocked ?o - obstacle ?l - location)
    (recharged ?b - battery)
  )
  (:action recharge
    :parameters (?r - robot ?b - battery ?l - location)
    :precondition (and (at ?r ?l) (on-ground ?b ?l) (blocked ?r ?l))
    :effect (and (recharged ?b) (not (blocked ?r ?l)))
  )
  (:action move
    :parameters (?r - robot ?l1 - location ?l2 - location)
    :precondition (and (at ?r ?l1) (not (recharged ?b)))
    :effect (and (at ?r ?l2) (not (at ?r ?l1)))
  )
)