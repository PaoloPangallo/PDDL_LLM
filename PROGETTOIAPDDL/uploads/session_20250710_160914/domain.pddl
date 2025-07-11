(define (domain cyber-heist-mission)
    (:requirements :strips :typing)
    (:types
        entity
        agent           - entity
        npc             - entity
        security_system - object
        credential      - object
        device          - object
        artifact        - object
        location
        house           - location
    )
    (:predicates
        (at ?x - entity ?l - location)
        (connected ?from - location ?to - location)
        (hacked ?o - object)
        (has ?h - agent ?o - object)
        (delivered ?o - object)
    )
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
    (:action hack-cctv
        :parameters (
        ?h - agent
        ?g - security_system
        ?l - location
        )
        :precondition (and
            (at ?h ?l)
            (at ?g ?l)
        )
        :effect (and
            (hacked ?g)
        )
    )
    (:action bribe-insider
        :parameters (
        ?h - agent
        ?i - npc
        ?c - credential
        ?l - location
        )
        :precondition (and
            (at ?h ?l)
            (at ?i ?l)
            (at ?c ?l)
        )
        :effect (and
            (has ?h ?c)
            (not (at ?c ?l))
        )
    )
    (:action hack-mainframe-via-cctv
        :parameters (
        ?h - agent
        ?m - device
        ?l - location
        ?g - security_system
        )
        :precondition (and
            (at ?h ?l)
            (at ?m ?l)
            (hacked ?g)
        )
        :effect (and
            (hacked ?m)
        )
    )
    (:action hack-mainframe-via-override
        :parameters (
        ?h - agent
        ?m - device
        ?l - location
        ?c - credential
        )
        :precondition (and
            (at ?h ?l)
            (at ?m ?l)
            (has ?h ?c)
        )
        :effect (and
            (hacked ?m)
        )
    )
    (:action transfer-ai
        :parameters (
        ?h - agent
        ?o - artifact
        ?l - location
        ?m - device
        )
        :precondition (and
            (at ?h ?l)
            (at ?o ?l)
            (hacked ?m)
        )
        :effect (and
            (has ?h ?o)
            (not (at ?o ?l))
        )
    )
    (:action escape-rooftop
        :parameters (
        ?h - agent
        ?from - location
        ?to - location
        ?o - artifact
        )
        :precondition (and
            (at ?h ?from)
            (connected ?from ?to)
            (has ?h ?o)
        )
        :effect (and
            (at ?h ?to)
            (not (at ?h ?from))
        )
    )
    (:action escape-metro
        :parameters (
        ?h - agent
        ?from - location
        ?to - location
        ?o - artifact
        )
        :precondition (and
            (at ?h ?from)
            (connected ?from ?to)
            (has ?h ?o)
        )
        :effect (and
            (at ?h ?to)
            (not (at ?h ?from))
        )
    )
    (:action deliver-ai
        :parameters (
        ?h - agent
        ?o - artifact
        ?c - house
        )
        :precondition (and
            (at ?h ?c)
            (has ?h ?o)
        )
        :effect (and
            (delivered ?o)
        )
    )
)