(define (problem my-domain-problem)
  (:domain my-domain)
  (:objects
    hero - agent
  )
  (:init
    (at hero village)
    (on_ground sword_of_fire village)
    (sleeping ice_dragon)
  )
  (:goal (and (at hero tower) (on_ground sword_of_fire tower) (defeated ice_dragon)))
)