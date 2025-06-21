(define (domain travel-world))
  (:requirements :strips)
  (:types location agent)
  (:predicates
    (at ?a - agent ?l - location)
    (on-water ?l - location)
    (on-path ?l1 - location ?l2 - location))

  (:action move
    :parameters (?a - agent ?from - location ?to - location)
    :precondition (and (at ?a ?from) (on-path ?from ?to))
    :effect (and (not (at ?a ?from)) (at ?a ?to)))

  (:action swim
    :parameters (?a - agent ?l - location)
    :precondition (and (at ?a ?l) (on-water ?l))
    :effect (or (and (at ?a (find-neighboring-land ?l)) (not (on-water ?l))) (and (not (at ?a (find-neighboring-land ?l))) (and (on-water ?l) (exists (?neighbor) (and (on-path ?neighbor ?l) (at ?neighbor (find-neighboring-land ?neighbor))))))))

  (:action find-neighboring-land
    :parameters (?l - location)
    :precondition (on-water ?l)
    :effect (exists (?neighbor) (and (on-path ?neighbor ?l) (at ?neighbor (find-neighboring-land ?neighbor))))))
  (:action reach-destination
    :parameters (?a - agent)
    :precondition (at ?a location2)
    :effect (true))

  (:invariant (and (on-path location1 location2) (implies (at ?a location2) (or (= ?a agent1) (exists (?neighbor) (and (on-path ?neighbor location2) (reachable ?neighbor)))))))

  (:fun find-neighboring-land-function (?l - location) (find-neighboring-land ?l))
  (:fun reachable-function (?a - agent) (reach-destination ?a))

  (:registration
    (type_synonym agent travel-agent)
    (predicate_synonym on-path_synonym (on-path ?l1 - location ?l2 - location))
    (function_synonym find-neighboring-land_synonym (find-neighboring-land ?l - location)))
  (:fun reachable-function (?a - travel-agent) (reach-destination ?a))

  (:typed-predicate (on-path ?l1 - location_type ?l2 - location_type))
  (:typed-action move (move travel-agent location_type location_type))
  (:typed-action swim (swim travel-agent location_type))
  (:typed-action find-neighboring-land (find-neighboring-land location_type))
  (:typed-action reach-destination (reach-destination travel-agent))