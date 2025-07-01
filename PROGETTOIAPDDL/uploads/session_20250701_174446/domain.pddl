(:requirements :strips :equality :typing :fluents)
   (:types agent monster location object)
   (:predicates
      (at ?a ?l)
      (on-ground ?o ?l)
      (carrying ?a ?o)
      (awake ?m)
      (defeated ?m)
      (at-location ?l))
   (:action move
      (:parameters (?a - agent) (?l1 - location) (?l2 - location))
      (:effect (at ?a ?l2)
               (not (at ?a ?l1)))
      :precondition (and (at ?a ?l1)))
   (:action take
      (:parameters (?a - agent) (?o - object) (?l - location))
      (:effect (carrying ?a ?o)
               (not (on-ground ?o ?l)))
      :precondition (and (at ?a ?l) (on-ground ?o ?l)))
   (:action drop
      (:parameters (?a - agent) (?o - object) (?l - location))
      (:effect (on-ground ?o ?l)
               (not (carrying ?a ?o)))
      :precondition (and (carrying ?a ?o) (at ?a ?l)))
   (:action wakeup
      (:parameters (?m - monster))
      (:effect (awake ?m))
      :precondition (sleeping ?m))
   (:action defeat
      (:parameters (?h - agent) (?m - monster))
      (:effect (defeated ?m))
      :precondition (and (carrying ?h sword-of-fire) (awake ?m)))