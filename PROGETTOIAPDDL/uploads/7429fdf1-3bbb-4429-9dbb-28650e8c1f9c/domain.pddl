(define (domain world_travel))
  (:requirements :strips)
  (:types location person)
  (:predicates
    (at ?p - person ?l - location)
    (nearby ?l1 - location ?l2 - location)
  )

  (:action travel
    :parameters (?p - person ?from - location ?to - location)
    :precondition (and (at ?p ?from) (nearby ?from ?to))
    :effect (and (not (at ?p ?from)) (at ?p ?to))
  )
  (:action rest
    :parameters (?p - person)
    :precondition (at ?p ?l)
    :effect (and (not (at ?p ?l)))
  )
  (:action observe
    :parameters (?p - person ?l1 - location ?l2 - location)
    :precondition (at ?p ?l1)
    :effect (if (nearby ?l1 ?l2) (nearly_visible ?l2))
  )

  (:action nearly_visible <observation>
    :parameters (?p - person ?obs - observation)
    :precondition (and (at ?p ?l) (observe_location ?obs ?l))
    :effect (if (visible ?l) (true_visibility ?l))
  )
  (:action visible <observation>
    :parameters (?p - person ?obs - observation)
    :precondition (and (at ?p ?l) (true_visibility ?l))
    :effect (if (visible ?l) (confirmed_visible ?l)))