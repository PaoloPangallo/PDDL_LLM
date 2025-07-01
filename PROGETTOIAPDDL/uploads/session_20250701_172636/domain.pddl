(:requirements :strips :equality :typing :qualified :negative-preconditions)
   (:types agent location object monster)
   (:predicates
      (at agent location)
      (on-ground object location)
      (carrying agent object)
      (awake monster)
      (sleeping monster))
   (:action move
      :parameters (?a - agent) (?l1 - location) (?l2 - location)
      :precondition (and (at ?a ?l1) (not (= ?l1 ?l2)))
      :effect (and (at ?a ?l2) (not (at ?a ?l1))))
   (:action take
      :parameters (?a - agent) (?o - object) (?l - location)
      :precondition (and (on-ground ?o ?l) (at ?a ?l))
      :effect (and (not (on-ground ?o ?l)) (carrying ?a ?o)))
   (:action drop
      :parameters (?a - agent) (?o - object)
      :precondition (and (carrying ?a ?o))
      :effect (and (at ?o on-ground) (not (carrying ?a ?o))))
   (:action fight
      :parameters (?a - agent) (?m - monster)
      :precondition (and (carrying ?a sword-of-fire) (awake ?m))
      :effect (and (sleeping ?m) (not (carrying ?a sword-of-fire))))