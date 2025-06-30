(define (domain quest)
       (:requirements :equality :quantifiers :strips)
       (:types agent location object dragon hero sword)
       (:predicates
        (at ?x ?loc)
        (on-ground ?o ?loc)
        (carrying ?h ?o)
        (awake ?d)
        (defeated ?d))

       (:action pickup
        :parameters (?h ?o ?l)
        :precondition (and (at ?h ?l) (on-ground ?o ?l))
        :effect (and (not (on-ground ?o ?l)) (carrying ?h ?o)))

       (:action putdown
        :parameters (?h ?o ?l)
        :precondition (and (carrying ?h ?o) (at ?h ?l))
        :effect (and (on-ground ?o ?l) (not (carrying ?h ?o))))

       (:action move
        :parameters (?x ?from ?to)
        :precondition (at ?x ?from)
        :effect (at ?x ?to))