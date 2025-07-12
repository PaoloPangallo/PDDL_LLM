(define (problem rescue-mission)
    (:domain rescue)
    (:objects
        hero - agent
        d1 - door
        room1 room2 - room
        elsa - villager
    )
    (:init
        (at hero room1)
        (villager_in elsa room2)
        (door_locked d1)
        (door_between d1 room1 room2)
    )
    (:goal (rescued elsa))
)