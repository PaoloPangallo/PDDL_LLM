(define (domain dragon-quest)
    (:requirements :strips :typing :adl)
    (:types
        agent
        monster
        object
        location
    )
    (:predicates        (at            ?h - agent            ?l - location        )        (sleeping            ?d - monster        )        (connected            ?from - location            ?to - location        )        (defeated            ?m - monster        )        (explored            ?l - location        )        (rested            ?h - agent        )        (has            ?h - agent            ?o - object        )        (forest_amulet            ?a - object        )        (cave_shield            ?a - object        )    )
    (:action move
        :parameters (
        ?h - agent
        ?from - location
        ?to - location
        )
        :precondition (and
            (at ?h ?from)
            (connected ?from ?to)
        )
        :effect (and
            (at ?h ?to)
            (not (at ?h ?from))
        )
    )
    (:action explore
        :parameters (
        ?h - agent
        ?l - location
        )
        :precondition (and
            (at ?h ?l)
            (not (explored ?l))
        )
        :effect (and
            (explored ?l)
        )
    )
    (:action rest
        :parameters (
        ?h - agent
        ?l - location
        )
        :precondition (and
            (at ?h ?l)
        )
        :effect (and
            (rested ?h)
        )
    )
    (:action defeat-monster
        :parameters (
        ?h - agent
        ?m - monster
        ?l - location
        )
        :precondition (and
            (at ?h ?l)
            (at ?m ?l)
        )
        :effect (and
            (defeated ?m)
        )
    )
    (:action pickup
        :parameters (
        ?h - agent
        ?o - object
        ?l - location
        )
        :precondition (and
            (at ?h ?l)
            (at ?o ?l)
        )
        :effect (and
            (has ?h ?o)
            (not (at ?o ?l))
        )
    )
    (:action defeat-dragon
        :parameters (
        ?h - agent
        ?d - monster
        ?l - location
        ?a - object
        )
        :precondition (and
            (at ?h ?l)
            (has ?h ?a)
            (explored ?l)
        (or
                (forest_amulet ?a)
                (cave_shield ?a)
        )
        )
        :effect (and
            (defeated ?d)
            (not (sleeping ?d))
        )
    )
)