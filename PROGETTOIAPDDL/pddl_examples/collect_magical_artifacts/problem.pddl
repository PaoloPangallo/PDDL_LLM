(define (problem artifact-hunt-problem)
    (:domain artifact-hunt)
    (:objects
        wizard - agent
        wand orb cloak - item
        cave forest tower - location
    )
    (:init
        (at wizard cave)
        (item_at wand forest)
        (item_at orb tower)
        (item_at cloak cave)
    )
    (:goal
        (and (has wizard wand) (has wizard orb) (has wizard cloak))
    )
)