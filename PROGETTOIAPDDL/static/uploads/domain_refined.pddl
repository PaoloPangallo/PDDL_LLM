(define (domain quest-domain)
  ; Domain declaration with name "quest-domain"
  (:types
    ; Define types used in the domain: agent, object, location, monster
    agent object location monster
  )

  (:predicates
    ; Agent predicates - describe where agents are and what they're carrying
    (at ?a - agent ?l - location)
    (carrying ?a - agent ?o - object)

    ; Object predicates - describe where objects are located
    (on-ground ?o - object ?l - location)

    ; Monster predicates - describe monster states
    (sleeping ?m - monster)
    (defeated ?m - monster)
  )

  (:action move-agent
    ; Action to move an agent from one location to another
    :parameters (?a - agent ?from - location ?to - location)
    :precondition (and (at ?a ?from))
    ; Agent must be at the starting location
    :effect (and (not (at ?a ?from)) (at ?a ?to))
    ; Agent is no longer at the start location and is now at the destination
  )

  (:action pick-object
    ; Action to pick up an object from the ground
    :parameters (?a - agent ?o - object ?l - location)
    :precondition (and (at ?a ?l) (on-ground ?o ?l))
    ; Agent must be at the same location as the object and the object must be on the ground
    :effect (and (not (on-ground ?o ?l)) (carrying ?a ?o))
    ; Object is no longer on the ground and is now carried by the agent
  )

  (:action drop-object
    ; Action to drop an object onto the ground
    :parameters (?a - agent ?o - object ?l - location)
    :precondition (and (at ?a ?l) (carrying ?a ?o))
    ; Agent must be at the location and carrying the object
    :effect (and (not (carrying ?a ?o)) (on-ground ?o ?l))
    ; Object is no longer carried by the agent and is now on the ground
  )

  (:action defeat-monster
    ; Action to defeat a monster using an object (weapon)
    :parameters (?a - agent ?m - monster ?o - object ?l - location)
    :precondition (and (at ?a ?l) (carrying ?a ?o) (sleeping ?m))
    ; Agent must be at the same location as the monster, carrying a weapon, and the monster must be sleeping
    :effect (defeated ?m)
    ; Monster is now defeated
  )
)