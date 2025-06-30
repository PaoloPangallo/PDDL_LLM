(define (domain hero-quest)
       (:requirements :equality :deterministic :negative-preconditions :static)

       (:types location action agent creature goal)

       (:predicates
        (at ?a location)
        (on-ground ?i item location)
        (carrying ?h ?i item)
        (awake ?c creature)
        (sleeping ?c creature)
        (defeated ?c creature))

       (:action move
         :parameters (?a agent) (?l location)
         :precondition (at ?a ?l)
         :effect (not (at ?a ?l))
         :effect (at ?a ?l))

       (:action take
         :parameters (?h agent) (?i item)
         :precondition (and (on-ground ?i ?l) (at ?h ?l))
         :effect (not (on-ground ?i ?l))
         :effect (carrying ?h ?i))

       (:action drop
         :parameters (?h agent) (?i item)
         :precondition (and (carrying ?h ?i))
         :effect (at (find-entity) (location ?l))
         :effect (on-ground ?i ?l)
         :effect (not (carrying ?h ?i)))

       (:action wake-creature
         :parameters (?c creature)
         :precondition (at hero ?l) (not (awake ?c))
         :effect (awake ?c))

       (:action defeat
         :parameters (?h agent) (?c creature)
         :precondition (and (carrying weapon-for-defeating ?h) (awake ?c))
         :effect (defeated ?c))
   )