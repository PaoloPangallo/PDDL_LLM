(define (domain reach-and-defeat)
  (:requirements :strips :typing)
  (:types location item dragon hero)
  (:predicates
    (at ?x - object ?loc - location)
    (on_ground ?x - item ?loc - location)
    (sleeping ?x - dragon)
    (carrying ?a - hero ?o - item)
    (defeated ?x - dragon))
  (:action move-to
    :parameters (?h - hero ?l1 - location ?l2 - location)
    :precondition (and (at ?h ?l1) (not (at ?h ?l2)))
    :effect (and (at ?h ?l2)))
  (:action pick-up
    :parameters (?h - hero ?s - sword_of_fire ?l - location)
    :precondition (and (at ?h ?l) (on_ground ?s ?l))
    :effect (and (carrying ?h ?s) (not (on_ground ?s ?l))))
  (:action defeat-dragon
    :parameters (?h - hero ?d - ice_dragon ?l - location)
    :precondition (and (at ?h ?l) (carrying ?h ?s) (sleeping ?d))
    :effect (and (defeated ?d)))
)