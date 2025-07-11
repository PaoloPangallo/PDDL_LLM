(define (problem cyber-heist-problem)
    (:domain cyber-heist-mission)
    (:objects
        
        hacker           - agent
        
        cctv_grid        - object
        
        insider          - agent
        
        override_code    - object
        
        ai_core          - object
        
        mainframe        - object
        
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
        
    )
    (:goal (and
        
        (at hacker safehouse)
        
        (delivered ai_core)
        
    ))
)