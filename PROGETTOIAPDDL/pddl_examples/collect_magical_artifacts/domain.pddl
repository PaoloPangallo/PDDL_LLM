(define (domain artifact-hunt)
    (:requirements :strips :typing)
    (:types agent item location)

    (:predicates
        (at ?a - agent ?l - location)
        (has ?a - agent ?i - item)
        (item_at ?i - item ?l - location)
    )

    (:action move
        :parameters (?a - agent ?from - location ?to - location)
        :precondition (at ?a ?from)
        :effect (and (not (at ?a ?from)) (at ?a ?to))
    )

    (:action collect
        :parameters (?a - agent ?i - item ?l - location)
        :precondition (and (at ?a ?l) (item_at ?i ?l))
        :effect (has ?a ?i)
    )
)