(define (problem xr17_recharge_mission_problem)
    (:domain xr17-recharge-mission)
    (:objects
        xr_17 - robot_type
        security_door - door_type
        control_panel - panel_type
        warehouse_drone_guard - drone_type
        warehouse_terminal - terminal_type
        emi_zone - zone_type
        patrolling_drone - drone_type
        emergency_battery_pack - battery_type
        hypercharge_dock - dock_type
        battery_swap_module - module_type
        start_loc - start_location_type
        door_cleared_loc - door_cleared_location_type
        warehouse_entrance_loc - warehouse_entrance_location_type
        emi_cleared_loc - emi_cleared_location_type
        drone_cleared_loc - drone_cleared_location_type
        battery_pickup_loc - battery_pickup_location_type
        central_charging_station_loc - charging_station_location_type
    )
    (:init
        (at xr_17 start_loc)
        (panel_damaged control_panel)
        (door_sealed security_door)
        (active warehouse_drone_guard)
        (terminal_available warehouse_terminal)
        (in_emi_zone emi_zone)
        (not_shielded)
        (drone_patrolling patrolling_drone)
        (battery_sufficient_stealth)
        (battery_sufficient_emp)
        (battery_available emergency_battery_pack)
        (dock_available hypercharge_dock)
        (module_available battery_swap_module)
        (battery_critical)
    )
    (:goal (and
        (at xr_17 central_charging_station_loc)
        (battery_full)
        (contact_established)
    ))
)