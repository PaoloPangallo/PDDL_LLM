(define (domain temple)
    (:requirements :strips :typing)
    (:types agent room artifact)

    (:predicates
        (at ?a - agent ?r - room)
        (connected ?r1 - room ?r2 - room)
        (has ?a - agent ?o - artifact)
        (artifact_in ?o - artifact ?r - room)
        (door_open ?r1 - room ?r2 - room)
    )

    (:action move
        :parameters (?a - agent ?from - room ?to - room)
        :precondition (and (at ?a ?from) (connected ?from ?to) (door_open ?from ?to))
        :effect (and (not (at ?a ?from)) (at ?a ?to))
    )

    (:action pick
        :parameters (?a - agent ?o - artifact ?r - room)
        :precondition (and (at ?a ?r) (artifact_in ?o ?r))
        :effect (has ?a ?o)
    )

    (:action open-door
        :parameters (?a - agent ?r1 - room ?r2 - room)
        :precondition (at ?a ?r1)
        :effect (door_open ?r1 ?r2)
    )
)