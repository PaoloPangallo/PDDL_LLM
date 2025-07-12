(define (domain rescue)
    (:requirements :strips :typing)
    (:types agent door villager room)

    (:predicates
        (at ?a - agent ?r - room)
        (door_locked ?d - door)
        (door_between ?d - door ?r1 - room ?r2 - room)
        (rescued ?v - villager)
        (villager_in ?v - villager ?r - room)
    )

    (:action unlock
        :parameters (?a - agent ?d - door)
        :precondition (door_locked ?d)
        :effect (not (door_locked ?d))
    )

    (:action move
        :parameters (?a - agent ?from - room ?to - room ?d - door)
        :precondition (and (at ?a ?from) (door_between ?d ?from ?to) (not (door_locked ?d)))
        :effect (and (not (at ?a ?from)) (at ?a ?to))
    )

    (:action rescue
        :parameters (?a - agent ?v - villager ?r - room)
        :precondition (and (at ?a ?r) (villager_in ?v ?r))
        :effect (rescued ?v)
    )
)