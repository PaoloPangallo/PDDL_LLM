(define (problem world-tour)
    (:domain world-travel)
    (:objects
      new-york - city
      paris - city
      london - city
      berlin - city
      moscow - city
      beijing - city
      sydney - city
      tokyo - city
      seoul - city
      rio - city
    )
    (:init
      (at new-york)
      (in-country new-york "USA")
      (explored new-york)
      (forall (?x - location)(not (or (in-city ?x) (explored ?x))))
    )
    (:goal (and (explored tokyo) (explored seoul)))
  )