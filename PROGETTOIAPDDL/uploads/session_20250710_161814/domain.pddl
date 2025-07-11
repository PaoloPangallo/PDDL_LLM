(define (domain robot-charge-mission)
    (:requirements :strips :typing)
    (:types
        entity
        agent      - entity
        npc        - entity
        battery    - object
        location
        station    - location
    )
    (:predicates
        (at ?x - entity ?l - location)
        (connected ?from - location ?to - location)
        (has ?r - agent ?b - battery)
        (recharged ?r - agent)
    )
    (:action move
        :parameters (
        ?r - agent
        ?from - location
        ?to - location
        )
        :precondition (and
            (at ?r ?from)
            (connected ?from ?to)
        )
        :effect (and
            (at ?r ?to)
            (not (at ?r ?from))
        )
    )
    (:action pickup-battery
        :parameters (
        ?r - agent
        ?b - battery
        ?l - location
        ?d - npc
        )
        :precondition (and
            (at ?r ?l)
            (at ?b ?l)
            (at ?d ?l)
        )
        :effect (and
            (has ?r ?b)
            (not (at ?b ?l))
        )
    )
    (:action hypercharge
        :parameters (
        ?r - agent
        ?s - station
        )
        :precondition (and
            (at ?r ?s)
        )
        :effect (and
            (recharged ?r)
        )
    )
    (:action swap-battery
        :parameters (
        ?r - agent
        ?b - battery
        ?s - station
        )
        :precondition (and
            (at ?r ?s)
            (has ?r ?b)
        )
        :effect (and
            (recharged ?r)
            (not (has ?r ?b))
        )
    )
)