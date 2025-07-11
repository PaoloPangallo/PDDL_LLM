(define (problem robot-charge-problem)
    (:domain robot-charge-mission)
    (:objects
        xr17               - agent
        drone              - npc
        emergency_battery  - battery
        corridor           - location
        warehouse          - location
        charging_station   - station
    )
    (:init
        (at xr17 corridor)
        (at drone warehouse)
        (at emergency_battery warehouse)
        (connected corridor charging_station)
        (connected charging_station corridor)
        (connected corridor warehouse)
        (connected warehouse corridor)
    )
    (:goal (and
        (at xr17 charging_station)
        (recharged xr17)
    ))
)