(define (domain delivery)
  (:requirements :strips :typing)
  (:types
    location
    truck
    package
  )
  (:predicates
    (at ?truck ?location)
    (has_package ?truck ?package)
    (in ?package ?location)
  )
  (:action move
    :parameters (?truck ?from ?to)
    :precondition (and (at ?truck ?from) (has_package ?truck ?package))
    :effect (and (not (at ?truck ?from)) (at ?truck ?to))
  )
  (:action pick
    :parameters (?truck ?package)
    :precondition (and (at ?truck ?location) (in ?package ?location))
    :effect (and (has_package ?truck ?package) (not (in ?package ?location)))
  )
  (:action drop
    :parameters (?truck ?package)
    :precondition (and (at ?truck ?location) (has_package ?truck ?package))
    :effect (and (not (has_package ?truck ?package)) (in ?package ?location))
  )
)

(define (problem delivery_problem)
  (:domain delivery)
  (:objects
    truck1 - truck
    truck2 - truck
    package1 - package
    package2 - package
    location1 - location
    location2 - location
    location3 - location
  )
  (:init
    (at truck1 location1)
    (at truck2 location2)
    (has_package truck1 package1)
    (has_package truck2 package2)
    (in package1 location1)
    (in package2 location2)
  )
  (:goal
    (and (at truck1 location2) (at truck2 location3) (has_package truck1 package1) (has_package truck2 package2))
  )
)