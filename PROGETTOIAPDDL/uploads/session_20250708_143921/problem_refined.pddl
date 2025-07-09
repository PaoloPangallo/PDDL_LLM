(define (problem logistics-prob)
  (:domain logistics)
  (:objects
    city1 city2 - city
    loc1 loc2 loc3 loc4 - place
    pkg1 pkg2 - package
    truck1 - truck ; Added 'truck' object
  )
  (:init
    (in-city loc1 city1)
    (in-city loc2 city1)
    (at pkg1 loc1)
    (at pkg2 loc2)
    (at truck1 loc1)
  )
  (:goal (and
    (in pkg1 truck1)
    (in pkg2 truck1)
  ))
)