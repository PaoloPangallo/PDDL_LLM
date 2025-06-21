(define (domain world-travel)
    (:requirements :strips)
    (:types location city country)
    (:predicates
      (at ?x - location)
      (in-city ?x - location)
      (in-country ?x - location)
      (neighboring-cities ?x - city ?y - city)
      (neighboring-countries ?x - country ?y - country)
    )

    (:action travel
      :parameters (?from - location ?to - location)
      :precondition (and (at ?from) (in-city ?from))
      :effect (and (not (at ?from)) (at ?to))
    )
  )
  (:action move-within-city
    :parameters (?x - city ?from - location ?to - location)
    :precondition (and (in-city ?x) (at ?from))
    :effect (and (not (at ?from)) (at ?to))
  )
  (:action cross-border
    :parameters (?from - location ?to - location)
    :precondition (and (at ?from) (in-country ?from))
    :effect (and (not (at ?from)) (in-country ?to))
  )
  (:action explore-neighboring-cities
    :parameters (?city - city)
    :precondition (in-city ?city)
    :effect (forall (?x - location)(neighboring-cities ?city ?x iff (or (and (not (explored ?x)) (in-city ?x)))))
  )
  (:action explore-neighboring-countries
    :parameters (?country - country)
    :precondition (in-country ?country)
    :effect (forall (?x - location)(neighboring-countries ?country ?x iff (or (and (not (explored ?x)) (in-country ?x)))))
  )
  (:action mark-as-explored
    :parameters (?location - location)
    :precondition (at ?location)
    :effect (not (or (neighboring-cities ?location _) (neighboring-countries ?location _)))(explored ?location)
  )