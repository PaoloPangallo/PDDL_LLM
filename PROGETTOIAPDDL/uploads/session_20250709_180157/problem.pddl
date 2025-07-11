(define (problem my-domain-problem)
  (:domain my-domain)
  (:objects
    hero - agent
  )
  (:init
    (at hero village)
    (on_ground sword_of_fire village)
    (sleeping ice_dragon)
    (connected village forest)
    (connected forest tower)
    (connected village dark_cave)
    (connected dark_cave tower)
  )
  (:goal (and (at hero tower) (on_ground sword_of_fire tower) (defeated ice_dragon)))
)