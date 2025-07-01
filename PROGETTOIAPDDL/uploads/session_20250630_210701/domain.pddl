(define (domain robot)
  (:requirements :strips :typing)
  (:types
    robot - robot
    box - box
    table - table
    wall - wall
  )
  (:predicates
    (at ?x - robot ?y - location)
    (on-table ?x - box ?y - table)
    (on-wall ?x - box ?y - wall)
  )
  (:action move
    :parameters (?x - robot ?y - location)
    :precondition (and (at ?x ?z) (not (at ?x ?y)))
    :effect (and (at ?x ?y) (not (at ?x ?z)))
  )
  (:action pick-up
    :parameters (?x - robot ?y - box ?z - table)
    :precondition (and (at ?x ?z) (on-table ?y ?z) (not (on-wall ?y ?z)))
    :effect (and (at ?x ?z) (on-wall ?y ?z) (not (on-table ?y ?z)))
  )
  (:action put-down
    :parameters (?x - robot ?y - box ?z - wall)
    :precondition (and (at ?x ?z) (on-wall ?y ?z) (not (on-table ?y ?z)))
    :effect (and (at ?x ?z) (on-table ?y ?z) (not (on-wall ?y ?z)))
  )
)