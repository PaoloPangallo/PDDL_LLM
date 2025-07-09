(define (problem logistics-prob)
  (:domain logistics)
  (:objects
    city1 city2 - city
    loc1 loc2 loc3 loc4 - place
    pkg1 pkg2 - package
    truck1 - vehicle
  )
  (:init
    (in-city loc1 city1)
    (at pkg1 loc1) ; Initially at loc1, will be moved to truck later.
    (at pkg2 loc2)
    (at truck1 loc1)
    (not (at pkg1 loc1)) ; This condition is now redundant due to planned effect in load-truck action.
  )
  (:goal (and (in pkg1 truck1) (in pkg2 truck1)))
)