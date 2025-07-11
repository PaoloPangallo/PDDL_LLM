(define (problem hero-journey-problem)
  (:domain hero-journey)
  (:objects
    hero - agent
    sword_of_fire - object
    ice_dragon - monster
    bandit - monster
    goblin - monster
    village - location
    forest - location
    dark_cave - location
    tower - location
  )
  (:init
    (at hero village)
    (on_ground sword_of_fire village)
    (sleeping ice_dragon)
    (connected village forest)
    (connected forest tower)
    (connected village dark_cave)
    (connected dark_cave tower)
    (at bandit forest)
    (at goblin dark_cave)
  )
  (:goal (and
    (defeated ice_dragon)
    (at hero village)
    (on_ground sword_of_fire village)
  ))
)