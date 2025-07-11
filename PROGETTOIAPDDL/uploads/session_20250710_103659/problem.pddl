(define (problem dragon-quest-problem)
  (:domain dragon-quest)
  (:objects
    hero - agent
    sword_of_fire - object
    forest_amulet - object
    cave_shield - object
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
    (has hero sword_of_fire)
    (at forest_amulet forest)
    (at cave_shield dark_cave)
    (at bandit forest)
    (at goblin dark_cave)
    (sleeping ice_dragon)
    (connected village forest)
    (connected forest tower)
    (connected village dark_cave)
    (connected dark_cave tower)
  )
  (:goal (and
    (defeated ice_dragon)
    (at hero village)
    (at sword_of_fire village)
  ))
)