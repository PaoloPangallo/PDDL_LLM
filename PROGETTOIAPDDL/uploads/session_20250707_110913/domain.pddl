(define (domain robot_recharge)
  (:requirements :strips :typing)
  (:types agent object location state)
  (:predicates
    (at ?x - object ?loc - location)
    (on_ground ?o - object ?s - state)
    (blocked ?loc - location))
  (:action move
    :parameters (?r - agent ?from - location ?to - location)
    :precondition (and (at ?r ?from) (not (blocked ?to)))
    :effect (and (not (at ?r ?from)) (at ?r ?to)))
  (:action charge
    :parameters (?b - object ?s - state)
    :precondition (and (on_ground ?b ?s) (at ?b ?s))
    :effect (and (not (on_ground ?b ?s)) (charged ?b))))