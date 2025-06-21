(define (problem world-tour)
    (:domain traveling-world)
    (:objects
      John - person
      NY - city
      DC - capital
      LA - city
    )
    (:init
      (at John NY)
      (city NY)
      (capital DC)
      (not (traveling-to John LA))
    )
    (:goal (and (at John LA)))
  )