(define (domain puzzle-game)
    (:requirements :strips)
    (:types player piece room goal)
    (:predicates
      (at ?p - player ?r - room)
      (has-piece ?p - player ?g - goal)
      (on ?p - player ?g - goal ?r - room)
      (in-room ?g - goal ?r - room)
      (goal-reached ?g - goal)
    )

    (:action move-player
      :parameters (?p - player ?from - room ?to - room)
      :precondition (and (at ?p ?from) (in-room ?p ?from))
      :effect (and (not (at ?p ?from)) (at ?p ?to) (in-room ?p ?to))
    )

    (:action pickup
      :parameters (?p - player ?g - goal)
      :precondition (and (at ?p room) (in-room ?g room))
      :effect (has-piece ?p ?g)
    )

    (:action place
      :parameters (?p - player ?g - goal ?r - room)
      :precondition (and (has-piece ?p ?g) (at ?p room))
      :effect (and (not (has-piece ?p ?g)) (on ?p ?g room ?r) (in-room ?g ?r))
    )

    (:action goal-reached
      :parameters (?g - goal)
      :precondition (goal-reached ?g)
      :effect nil ; this action is used to achieve the goal, but does not change the state
    )
  )