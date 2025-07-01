(:requirements :strips :equality)
   (:types agent monster location object)
   (:predicates
      (at - agent location)
      (on-ground - object location)
      (sleeping - monster)
      (carrying - agent object)
   )

   (:action move-to
      :parameters (?a - agent) (?l1 - location) (?l2 - location)
      :precondition (and (at ?a ?l1) (not (= ?l1 ?l2)))
      :effect (and (not (at ?a ?l1)) (at ?a ?l2))
   )

   (:action take
      :parameters (?a - agent) (?o - object)
      :precondition (and (on-ground ?o) (not (carrying ?a ?o)))
      :effect (and (not (on-ground ?o)) (carrying ?a ?o))
   )

   (:action drop
      :parameters (?a - agent) (?o - object)
      :precondition (carrying ?a ?o)
      :effect (and (on-ground ?o) (not (carrying ?a ?o)))
   )

   (:action fight
      :parameters (?h - hero) (?m - monster)
      :precondition (and (at ?h tower-of-varnak) (carrying sword-of-fire) (sleeping ?m))
      :effect (not (sleeping ?m))
   )