(define (problem world-tour)
       (:domain traveling-world)
       (:objects
         John - person
         NY - city
         DC - capital
         LA - city
         DC - capital)
       (:init
         (at John NY)
         (city NY)
         (capital DC)
         (not (traveling-to John LA))
         (city DC))
       (:goal (and (at John LA)))