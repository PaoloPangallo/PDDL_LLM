(define (domain robot-domain)
  (:requirements :strips :typing)
  (:types
    robot
    charging-station
    obstacle
    battery
    ground
  )
  (:predicates
    (at ?x ?y)
    (on-ground ?x ?y)
    (blocked ?x ?y)
  )
  (:action move
    :parameters (?x ?y)
    :precondition (and (at ?x ?y) (on-ground ?x ?y))
    :effect (and (not (at ?x ?y)) (at ?x ?z) (on-ground ?x ?z))
  )
  (:action recharge
    :parameters (?x)
    :precondition (and (at ?x charging-station) (on-ground ?x charging-station))
    :effect (and (not (on-ground ?x charging-station)) (on-ground ?x battery))
  )
)