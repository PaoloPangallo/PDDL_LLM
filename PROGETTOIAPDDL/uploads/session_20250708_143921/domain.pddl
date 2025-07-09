(define (domain logistics)
  (:requirements :strips :typing)
  (:types place physobj package vehicle truck city) ; Added 'city' type
  (:predicates
    (in-city ?loc - place ?city - city)
    (at      ?obj - physobj ?loc - place) ; Fixed arity for 'at' predicate
    (in      ?pkg - package ?veh - vehicle)
  )
  (:action load-truck
    :parameters (?pkg - package ?truck - truck ?loc - place)
    :precondition (and (at ?pkg ?loc) (at ?truck ?loc))
    :effect (and (not (at ?pkg ?loc)) (in ?pkg ?truck))
  )
  (:action drive-truck
    :parameters (?truck - truck ?from - place ?to - place)
    :precondition (at ?truck ?from)
    :effect (and (not (at ?truck ?from)) (at ?truck ?to))
  )
)