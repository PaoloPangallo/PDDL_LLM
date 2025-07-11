(define (problem helios-dynamics-robot-rescue-problem)
    (:domain helios-dynamics-robot-rescue)
    (:objects
        xr_17 - robot
        security_drone - drone_guard
        main_door_panel - door_panel
        warehouse_terminal - terminal
        em_shielding_coil - device
        emergency_battery - battery_unit
        hypercharge_dock - module
        battery_swap_module - module
        em_interference_zone - location
        warehouse - location
        maintenance_tunnel - location
        main_corridor - location
        central_charging_station - charging_station
    )
    (:init
        (at xr_17 main_corridor)
        (at main_door_panel main_corridor)
        (powered main_door_panel)
        (at security_drone maintenance_tunnel)
        (at warehouse_terminal maintenance_tunnel)
        (at em_shielding_coil warehouse)
        (has_battery_level xr_17 emergency_battery)
        (at hypercharge_dock central_charging_station)
        (at battery_swap_module central_charging_station)
        (connected main_corridor em_interference_zone)
        (connected em_interference_zone main_corridor)
        (connected em_interference_zone central_charging_station)
        (connected central_charging_station em_interference_zone)
        (connected main_corridor maintenance_tunnel)
        (connected maintenance_tunnel warehouse)
        (connected warehouse main_corridor)
    )
    (:goal (and
        (contact_restored xr_17)
    ))
)