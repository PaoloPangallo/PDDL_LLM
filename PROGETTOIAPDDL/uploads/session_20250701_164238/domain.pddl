(:domain quest-tower-of-varnak
    (:requirements :strips :equality :typing :quantifiers :negative-preconditions)
    (:types agent location object monster)
    (:predicates
     (at ?a -agent -location)
     (on-ground ?o -object -location)
     (sleeping ?m -monster))
    (:action move
      :parameters (?a -agent) (?l1 -location) (?l2 -location)
      :precondition (and (at ?a ?l1) (not (= ?l1 ?l2)))
      :effect (and (at ?a ?l2) (not (at ?a ?l1))))
    (:action take
      :parameters (?a -agent) (?o -object)
      :precondition (and (on-ground ?o) (at ?a tower-of-varnak))
      :effect (and (holding ?a ?o) (not (on-ground ?o))))
    (:action drop
      :parameters (?a -agent) (?o -object)
      :precondition (and (holding ?a ?o) (at ?a tower-of-varnak))
      :effect (and (on-ground ?o) (not (holding ?a ?o))))
    (:action fight
      :parameters (?a -agent) (?m -monster)
      :precondition (and (holding ?a sword-of-fire) (at ?a tower-of-varnak) (sleeping ?m))
      :effect (not (sleeping ?m))))