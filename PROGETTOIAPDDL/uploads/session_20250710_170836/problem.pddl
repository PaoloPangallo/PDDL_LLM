(define (problem xr17-escape-problem)
    (:domain xr17-escape)
    (:objects
        xr17 - robot
        blast_door - device
        access_terminal - device
        em_burst_tool - tool
        shielding_coil - tool
        emergency_battery - battery
        access_code - credential
        drone_guard - drone
        security_drone - drone
        sector_a3 - zone
        main_corridor - corridor
        warehouse - zone
        maintenance_tunnel - tunnel
        em_zone - zone
        charging_station - station
    )
    (:init
        (at xr17 sector_a3)
        (at blast_door main_corridor)
        (at access_terminal maintenance_tunnel)
        (at access_code maintenance_tunnel)
        (at drone_guard maintenance_tunnel)
        (at em_burst_tool warehouse)
        (at shielding_coil warehouse)
        (at emergency_battery warehouse)
        (at security_drone main_corridor)
        (connected sector_a3 main_corridor)
        (connected main_corridor em_zone)
        (connected em_zone charging_station)
        (connected sector_a3 warehouse)
        (connected warehouse maintenance_tunnel)
        (connected maintenance_tunnel main_corridor)
    )
    (:goal (and
        (contact_restored xr17)
    ))
)