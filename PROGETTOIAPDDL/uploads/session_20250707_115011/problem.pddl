(define (problem reach-the-tower)
  (:domain reach-and-defeat)
  (:objects
    hero1 - hero
    village - location
    tower_of_varnak - location
    sword_of_fire - item
    ice_dragon - dragon)
  (:init
    (at hero1 village)
    (on_ground sword_of_fire tower_of_varnak)
    (sleeping ice_dragon))
  (:goal
    (and
      (defeated ice_dragon)
      (carrying hero1 sword_of_fire)))
)