(define (domain logistics)
  (:requirements :strips :typing)
  (:types city place physobj package vehicle)
  (:predicates
    (in-city ?loc - place ?city - city)
    (at      ?obj - physobj ?loc - place)
    (in      ?pkg - package ?veh - vehicle)
  )
  (:action load-truck
    :parameters (?pkg - package ?truck - vehicle ?loc - place)
    :precondition (and (at ?pkg ?loc) (at ?truck ?loc))
    :effect (and (not (at ?pkg ?loc)) (in ?pkg ?truck))
  )
  (:action drive-truck
    :parameters (?truck - vehicle ?from - place ?to - place)
    :precondition (at ?truck ?from)
    :effect (and (not (at ?truck ?from)) (at ?truck ?to))
  )
)