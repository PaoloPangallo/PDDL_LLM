(define (problem infiltrate_halcyon_problem)
  (:domain infiltrate_halcyon)
  (:objects
    hacker - object
    location1 - location
    location2 - location
    core - target
  )
  (:init
    (at hacker location1)
    (has_access hacker location1)
    (can_disable hacker location1)
    (contains core location1)
    (at core location1)
  )
  (:goal
    (and
      (secured hacker)
    )
  )
)