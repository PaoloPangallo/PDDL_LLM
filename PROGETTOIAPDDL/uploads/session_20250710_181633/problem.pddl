(define (problem xr17-navigation-problem)
  (:domain xr17-navigation)
  (:objects
    a - location
    b - route
    c - method
  )
  (:init
    (at a)
    (reachable a)
    (has-route a b)
    (use-method c))
  (:goal
    (and (contact-restored)))
)