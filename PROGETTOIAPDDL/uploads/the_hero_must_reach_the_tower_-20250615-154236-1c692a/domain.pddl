(define (domain traveling-world)
    (:requirements :strips)
    (:types location person)
    (:predicates
      (at ?p - person ?l - location)
      (city ?c - location)
      (capital ?c - location)
      (traveling-to ?p - person ?t - location)
    )

    (:action move
      :parameters (?p - person ?from - location ?to - location)
      :precondition (and (at ?p ?from) (not (traveling-to ?p ?to)))
      :effect (and (not (at ?p ?from)) (at ?p ?to) (traveling-to ?p ?to))
    )

    (:action rest
      :parameters (?p - person)
      :precondition (and (at ?p ?location1) (city ?location1))
      :effect (not (traveling-to ?p ?location2))
    )
  )