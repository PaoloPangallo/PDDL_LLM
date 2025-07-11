(define (problem dragon-quest-problem)
    (:domain dragon-quest)
    (:objects
        hero - agent
        sword_of_fire - weapon
        forest_amulet - artifact
        cave_shield - artifact
        ice_dragon - boss
        bandit - normal_monster
        goblin - normal_monster
        village - location
        forest - location
        dark_cave - location
        tower - location
    )
    (:init
        (at hero village)
        (at sword_of_fire village)
        (at forest_amulet forest)
        (at cave_shield dark_cave)
        (at bandit forest)
        (at goblin dark_cave)
        (at ice_dragon tower)
        (sleeping ice_dragon)
        (connected village forest)
        (connected forest village)
        (connected village dark_cave)
        (connected dark_cave village)
        (connected forest tower)
        (connected tower forest)
        (connected dark_cave tower)
        (connected tower dark_cave)
    )
    (:goal (and
        (defeated ice_dragon)
        (at hero village)
        (at sword_of_fire village)
    ))
)