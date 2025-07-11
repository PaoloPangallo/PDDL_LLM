(define (problem cyber-heist-problem)
    (:domain cyber-heist-mission)
    (:objects
        hacker           - agent
        insider          - npc
        cctv_grid        - security_system
        override_code    - credential
        mainframe        - device
        ai_core          - artifact
        safehouse        - location
        network_hub      - location
        glitterbar       - location
        skyscraper       - location
        rooftop_helipad  - location
        metro_tunnel     - location
    )
    (:init
        (at hacker safehouse)
        (at cctv_grid network_hub)
        (at insider glitterbar)
        (at override_code glitterbar)
        (at mainframe skyscraper)
        (at ai_core skyscraper)
        (connected safehouse network_hub)
        (connected network_hub safehouse)
        (connected safehouse glitterbar)
        (connected glitterbar safehouse)
        (connected network_hub skyscraper)
        (connected skyscraper network_hub)
        (connected glitterbar skyscraper)
        (connected skyscraper glitterbar)
        (connected skyscraper rooftop_helipad)
        (connected rooftop_helipad skyscraper)
        (connected skyscraper metro_tunnel)
        (connected metro_tunnel skyscraper)
        (connected metro_tunnel safehouse)
        (connected safehouse metro_tunnel)
    )
    (:goal (and
        (at hacker safehouse)
        (delivered ai_core)
    ))
)