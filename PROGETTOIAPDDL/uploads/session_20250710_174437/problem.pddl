(define (problem xr17-mission-problem)
    (:domain xr17-mission)
    (:objects
        xr17 - robot
        security_drone - drone
        blast_door - door
        warehouse_terminal - terminal
        sector_a3 - plant_area
        main_corridor - corridor
        maintenance_tunnel - maintenance_tunnel
        em_zone - em_interference_zone
        charging_station - charging_station
        hypercharge_dock - charging_dock
        battery_swap_module - charging_dock
        magnetic_shield_coil - em_shield_coil
        emergency_battery - emergency_battery
    )
    (:init
        (at xr17 sector_a3)
        (at blast_door main_corridor)
        (door_locked blast_door)
        (at warehouse_terminal maintenance_tunnel)
        (at security_drone maintenance_tunnel)
        (at magnetic_shield_coil warehouse_terminal)
        (at hypercharge_dock charging_station)
        (at battery_swap_module charging_station)
        (battery_critical xr17)
        (connected sector_a3 main_corridor)
        (connected main_corridor maintenance_tunnel)
        (connected maintenance_tunnel warehouse_terminal)
        (connected main_corridor em_zone)
        (connected em_zone charging_station)
    )
    (:goal (and
        (recharged xr17)
    ))
)