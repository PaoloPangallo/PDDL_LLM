(define (domain my-domain)
  (:requirements :strips :typing)
  (:types agent location object)
  (:predicates
    (at ?r - agent ?l - location)
    (on_ground ?b - object ?l - location)
    (blocked ?obstacle - object ?charging_station - location)
    (charged ?b - object)
    (carrying ?r - agent ?b - object)
  )

  (:action move
    :parameters (?r - agent ?from - location ?to - location ?obstacle - object)
    :precondition (and (at ?r ?from) (not (blocked ?obstacle ?to)))
    :effect       (and (not (at ?r ?from)) (at ?r ?to))
  )

  (:action pickup-battery
    :parameters (?r - agent ?b - object ?l - location)
    :precondition (and (at ?r ?l) (on_ground ?b ?l))
    :effect       (and (carrying ?r ?b) (not (on_ground ?b ?l)))
  )

  (:action insert-battery
    :parameters (?r - agent ?b - object ?l - location ?charging_station - location)
    :precondition (and (carrying ?r ?b) (at ?r ?l) (= ?l ?charging_station))
    :effect       (and (charged ?b))
  )
)