(define (domain robot-domain)
  (:requirements :strips :typing)
  (:types
    robot
    charging-station
    obstacle
    ground
    battery)
  (:predicates
    (at ?r - robot ?l - location)
    (on-ground ?b - battery ?l - location)
    (blocked ?o - obstacle ?l - location))
  (:action move-robot
    :parameters (?r - robot ?l1 - location ?l2 - location)
    :precondition (and (at ?r ?l1) (not (blocked ?o ?l1)))
    :effect (and (not (at ?r ?l1)) (at ?r ?l2)))
  (:action recharge
    :parameters (?r - robot ?b - battery)
    :precondition (and (at ?r charging-station) (on-ground ?b charging-station))
    :effect (and (not (on-ground ?b charging-station)) (on-ground ?b ?r)))
  (:action clear-obstacle
    :parameters (?o - obstacle ?l - location)
    :precondition (and (at ?o ?l) (blocked ?o ?l))
    :effect (not (blocked ?o ?l))))
)