(define (domain dragon-and-sword)
     (:requirements :equality :deterministic :negative-preconditions :static)

     (:types agent location dragon sword)

     (:predicates
      (at ?a ?l location)
      (on-ground ?s ?o sword)
      (carrying ?h ?s sword)
      (sleeping ?d dragon)
      (awake ?d dragon)
      (defeated ?d dragon))

     (:action take
       :parameters (?h agent) (?s sword)
       :precondition (and (at ?h ?l) (on-ground ?s ?l))
       :effect (and (not (on-ground ?s ?l)) (carrying ?h ?s)))

     (:action drop
       :parameters (?h agent) (?s sword)
       :precondition (and (carrying ?h ?s))
       :effect (and (at (find-entity) (location ?l)) (on-ground ?s ?l) (not (carrying ?h ?s))))

     (:action wake-dragon
       :parameters (?d dragon)
       :precondition (at hero ?l) (not (sleeping ?d))
       :effect (awake ?d))

     (:action defeat-dragon
       :parameters (?h agent) (?d dragon)
       :precondition (and (carrying sword-of-fire ?h) (awake ?d))
       :effect (defeated ?d))
   )