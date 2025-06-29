(define (domain world_of_puzzles)
    (:requirements :strips)
    (:types location entity block object goal)
    (:predicates
      (on ?e1 - entity ?e2 - entity ?l - location)
      (clear ?l - location)
      (at ?o - object ?l - location)
      (goal_reached ?g - goal)
    )

    (:action move_entity
      :parameters (?e1 - entity ?from - location ?to - location)
      :precondition (and (on ?e1 nil ?from) (clear ?to))
      :effect (and (not (on ?e1 nil ?from)) (not (clear ?to)) (on ?e1 nil ?to) (clear ?from))
    )

    (:action pickup
      :parameters (?o - object ?e - entity ?l - location)
      :precondition (and (at ?e ?l) (on ?o nil ?l))
      :effect (and (not (on ?o nil ?l)) (held ?e ?o))
    )

    (:action putdown
      :parameters (?o - object ?e - entity ?l - location)
      :precondition (and (held ?e ?o))
      :effect (and (not (held ?e ?o)) (on ?o nil ?l))
    )

    (:action place_goal
      :parameters (?g - goal ?l - location)
      :precondition (clear ?l)
      :effect (and (at ?g ?l) (goal_reached ?g))
    )
  )