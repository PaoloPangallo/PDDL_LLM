(define (domain xr17-escape)
    (:requirements :strips :typing)
    (:types
        entity
        robot - entity
        drone - entity
        object - entity
        device - object
        tool - object
        battery - object
        credential - object
        location
        zone - location
        station - location
        corridor - location
        tunnel - location
    )
    (:predicates
        (at ?x - entity ?l - location)
        (connected ?from - location ?to - location)
        (has ?r - robot ?o - object)
        (disabled ?d - drone)
        (hacked ?d - device)
        (secured ?b - battery)
        (recharged ?r - robot)
        (contact_restored ?r - robot)
    )
    (:action move
        :parameters (
        ?r - robot
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
    (:action reroute-power
        :parameters (
        ?r - robot
        ?d - device
        ?l - location
        )
        :precondition (and
            (at ?r ?l)
            (at ?d ?l)
        )
        :effect (and
            (hacked ?d)
        )
    )
    (:action hack-access-code
        :parameters (
        ?r - robot
        ?t - device
        ?c - credential
        ?l - location
        ?d - drone
        )
        :precondition (and
            (at ?r ?l)
            (at ?t ?l)
            (at ?c ?l)
            (at ?d ?l)
            (disabled ?d)
        )
        :effect (and
            (has ?r ?c)
        )
    )
    (:action disable-drone
        :parameters (
        ?r - robot
        ?d - drone
        ?t - tool
        ?l - location
        )
        :precondition (and
            (at ?r ?l)
            (at ?d ?l)
            (has ?r ?t)
        )
        :effect (and
            (disabled ?d)
        )
    )
    (:action stealth-bypass
        :parameters (
        ?r - robot
        ?d - drone
        ?l - location
        )
        :precondition (and
            (at ?r ?l)
            (at ?d ?l)
        )
        :effect (and
            (disabled ?d)
        )
    )
    (:action grab-shielding
        :parameters (
        ?r - robot
        ?s - tool
        ?l - location
        )
        :precondition (and
            (at ?r ?l)
            (at ?s ?l)
        )
        :effect (and
            (has ?r ?s)
            (not (at ?s ?l))
        )
    )
    (:action grab-battery
        :parameters (
        ?r - robot
        ?b - battery
        ?l - location
        )
        :precondition (and
            (at ?r ?l)
            (at ?b ?l)
        )
        :effect (and
            (has ?r ?b)
            (not (at ?b ?l))
        )
    )
    (:action shielded-crossing
        :parameters (
        ?r - robot
        ?z - zone
        ?s - tool
        )
        :precondition (and
            (at ?r ?z)
            (has ?r ?s)
        )
        :effect (and
        )
    )
    (:action unshielded-sprint
        :parameters (
        ?r - robot
        ?z - zone
        )
        :precondition (and
            (at ?r ?z)
        )
        :effect (and
        )
    )
    (:action hypercharge
        :parameters (
        ?r - robot
        ?l - station
        )
        :precondition (and
            (at ?r ?l)
        )
        :effect (and
            (recharged ?r)
        )
    )
    (:action battery-swap
        :parameters (
        ?r - robot
        ?b - battery
        ?l - station
        )
        :precondition (and
            (at ?r ?l)
            (has ?r ?b)
        )
        :effect (and
            (recharged ?r)
        )
    )
    (:action restore-contact
        :parameters (
        ?r - robot
        )
        :precondition (and
            (recharged ?r)
        )
        :effect (and
            (contact_restored ?r)
        )
    )
)