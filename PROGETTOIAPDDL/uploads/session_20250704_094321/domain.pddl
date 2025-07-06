(define (domain robot-domain)
  (:requirements :strips :typing)
  (:types
    robot - robot
    charging-station - charging-station
    obstacle - obstacle
    battery - battery
    ground - ground)
  (:predicates
    (at ?r ?l)
    (on-ground ?b ?l)
    (blocked ?o ?l)
    (recharged ?b))
  (:action move-robot
    :parameters (?r ?l1 ?l2)
    :precondition (and (at ?r ?l1) (not (at ?r ?l2)))
    :effect (and (at ?r ?l2) (not (at ?r ?l1))))
  (:action recharge-battery
    :parameters (?b ?l)
    :precondition (and (on-ground ?b ?l) (at robot ?l))
    :effect (and (recharged ?b) (not (on-ground ?b ?l))))
  (:action clear-obstacle
    :parameters (?o ?l)
    :precondition (and (blocked ?o ?l) (at robot ?l))
    :effect (and (not (blocked ?o ?l)) (not (at robot ?l)))))