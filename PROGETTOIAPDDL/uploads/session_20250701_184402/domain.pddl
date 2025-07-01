(:domain quest-of-the-hero
    (:requirements :strips :equality :typing)
    (:types agent location object monster)
    (:predicates
     (at agent location)
     (on-ground object location)
     (carrying agent object)
     (awake monster)
     (defeated monster))

   (:action take-object
     :parameters (?a - agent) (?o - object)
     :effect (and (not (on-ground ?o ?a)) (carrying ?a ?o)))

   (:action drop-object
      :parameters (?a - agent) (?o - object)
      :effect (and (on-ground ?o ?a) (not (carrying ?a ?o))))

   (:action move-to
      :parameters (?a - agent) (?l - location)
      :effect (at ?a ?l)))

   (:action wake-monster
      :parameters (?m - monster)
      :effect (not (asleep ?m)))

   (:action defeat-monster
     :parameters (?a - agent) (?m - monster)
     :condition (and (carrying ?a sword-of-fire) (at ?a ?l))
     :effect (and (awake ?m) (defeated ?m)))